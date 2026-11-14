"""Tests for the raster readers of pipeline.minerals (VICAR, GeoTIFF, EMIT netCDF and coordinate handling).

Everything is synthetic; the real files are only on Yuca and in the Kaguya and ASU servers. The files are
written in the same layouts as the real ones, which were inspected on 2026-11-14.
"""

import math
from pathlib import Path

import numpy as np
import pytest
import rasterio
import rasterio.shutil
from rasterio.transform import from_origin

from pipeline.minerals import (
    EMIT,
    KAGUYA,
    TES,
    emit_origin,
    enrich_universe,
    grids_from_coords,
    load_emit_grids,
    load_geotiff_grid,
    load_vicar_grid,
    sample_source,
    summarize_mars,
)


def gdal_has_netcdf() -> bool:
    with rasterio.Env() as env:
        return "netCDF" in env.drivers()


def write_vicar(path: Path, data: np.ndarray, truncate: int = 0) -> None:
    """A VICAR file as the ASU WMS writes it: label of LBLSIZE bytes, then little-endian float32, north row first."""
    rows, cols = data.shape
    lblsize = 5760
    label = f"LBLSIZE={lblsize} HOST='PC' INTFMT='LOW' REALFMT='RIEEE' FORMAT='REAL' TYPE='IMAGE' NL={rows} NS={cols} NB=1"
    raw = label.encode("latin1").ljust(lblsize, b" ") + data.astype("<f4").tobytes()
    path.write_bytes(raw[: len(raw) - truncate] if truncate else raw)


# --- VICAR ----------------------------------------------------------------------------------------


def test_vicar_roundtrip_orientation_and_masking(tmp_path):
    data = np.zeros((720, 1440), dtype=np.float32)
    data[(90 - 45) * 4, (330) * 4] = 0.12  # 45N, 330E
    data[(90 - 18) * 4 + 1, 77 * 4] = -1.0  # masked cell near Jezero
    p = tmp_path / "tes_hematite.vic"
    write_vicar(p, data)
    grid = load_vicar_grid(p)
    assert grid.wraps and grid.rows == 720 and grid.cols == 1440
    assert grid.window_median(44.9, 330.1, 0, 0.0, 1.0) == pytest.approx(0.12)
    # longitude given as -30 (= 330 east) lands on the same cell
    assert grid.window_median(44.9, -29.9, 0, 0.0, 1.0) == pytest.approx(0.12)
    # the -1 mask is outside the valid range, so it does not count
    assert math.isnan(grid.window_median(17.6, 77.1, 0, 0.0, 1.0))


def test_vicar_truncated_file_is_refused(tmp_path):
    p = tmp_path / "tes_olivine.vic"
    write_vicar(p, np.zeros((720, 1440), dtype=np.float32), truncate=270_000)
    with pytest.raises(ValueError, match="truncated"):
        load_vicar_grid(p)


def test_vicar_without_label_is_refused(tmp_path):
    p = tmp_path / "x.vic"
    p.write_bytes(b"<html>401</html>" * 100)
    with pytest.raises(ValueError, match="not a VICAR"):
        load_vicar_grid(p)


# --- GeoTIFF (Kaguya layout) ----------------------------------------------------------------------


def test_geotiff_grid_kaguya_layout(tmp_path):
    arr = np.full((400, 1440), 0.05, dtype=np.float32)
    arr[200, 720] = 0.5  # row 200 is the equator, column 720 is longitude 0
    p = tmp_path / "olivine.tif"
    with rasterio.open(
        p, "w", driver="GTiff", height=400, width=1440, count=1, dtype="float32", crs="EPSG:4326",
        transform=from_origin(-180.0, 50.0, 0.25, 0.25),
    ) as dst:
        dst.write(arr, 1)
    grid = load_geotiff_grid(p)
    assert (grid.west, grid.east, grid.north, grid.south) == (-180.0, 180.0, 50.0, -50.0)
    assert grid.window_median(-0.1, 0.1, 0, 0.0, 1.0) == pytest.approx(0.5)
    # the same file gives a Kaguya answer inside 50N-50S and "outside_coverage" beyond it
    grids = {v.key: grid for v in KAGUYA.vars}
    assert sample_source(KAGUYA, grids, 10.0, 20.0)["status"] == "ok"
    assert sample_source(KAGUYA, grids, -85.0, 20.0)["status"] == "outside_coverage"


def test_kaguya_values_are_scaled_to_percent_and_outliers_dropped():
    fractions = Grid_from(np.full((8, 16), 0.25))
    feo = Grid_from(np.full((8, 16), 106.0))  # the Kaguya FeO map has a few absurd values; valid range is 0-30
    out = sample_source(KAGUYA, {"olivine": fractions, "feo": feo}, 0.0, 10.0)
    assert out["values"]["olivine"] == 25.0
    assert out["values"]["feo"] is None


def Grid_from(data):
    from pipeline.minerals import Grid

    return Grid(data, west=-180.0, east=180.0, north=50.0, south=-50.0)


# --- Mars summary ---------------------------------------------------------------------------------


def test_mars_summary_does_not_name_a_mineral_below_detection():
    s = summarize_mars({"olivine": 0.0, "orthopyroxene": 0.3, "clinopyroxene": 1.2, "plagioclase": 1.0, "hematite": 0.0})
    assert "No silicate above the TES detection level" in s
    assert "clinopyroxene" not in s


# --- EMIT coordinates and netCDF ------------------------------------------------------------------


def test_emit_origin_detects_corner_and_centre_values():
    # GDAL reads the first coordinates as centres: left = first_lon - dx/2, top = first_lat + dy/2
    left, top, corner = emit_origin(-172.25, 57.25, 0.5, 0.5, None)  # first values -172.0 and 57.0: multiples of 0.5
    assert corner and (left, top) == (-172.0, 57.0)
    left, top, corner = emit_origin(-172.0, 57.0, 0.5, 0.5, None)  # first values -171.75 and 56.75: centres
    assert not corner and (left, top) == (-172.0, 57.0)
    assert emit_origin(-172.0, 57.0, 0.5, 0.5, True)[2] is True  # forced


def test_grids_from_coords_descending_and_ascending_latitude():
    data = np.arange(12, dtype=np.float64).reshape(3, 4)
    lon = np.array([-10.0, -9.5, -9.0, -8.5])
    lat_desc = np.array([30.0, 29.5, 29.0])
    g = grids_from_coords({"hematite": data}, lat_desc, lon, corner=True)["hematite"]
    assert (g.west, g.east, g.north, g.south) == (-10.0, -8.0, 30.0, 28.5)
    assert g.window_median(29.9, -9.9, 0, 0, 100) == 0.0  # first cell
    # the same data with ascending latitude gives the same grid once flipped
    g2 = grids_from_coords({"hematite": data[::-1]}, lat_desc[::-1], lon, corner=True)["hematite"]
    assert np.array_equal(g.data, g2.data)
    # centre convention moves the grid half a cell
    gc = grids_from_coords({"hematite": data}, lat_desc + 0.25, lon + 0.25, corner=False)["hematite"]
    assert gc.north == pytest.approx(30.0 + 0.25 + 0.25) and gc.west == pytest.approx(-10.0)


def make_emit_netcdf(path: Path, corner_values: bool) -> None:
    """Write a netCDF with GDAL (CreateCopy) with the EMIT variable names, including an uncertainty variable."""
    height, width = 220, 690
    # cell edges at -172.0 .. 173.0 and 57.0 .. -53.0; GDAL writes cell centres, so this file uses centre values.
    # With corner_values the transform is shifted half a cell so that GDAL will read multiples of 0.5.
    shift = 0.25 if corner_values else 0.0
    transform = from_origin(-172.0 - shift, 57.0 + shift, 0.5, 0.5)
    names = ["Calcite", "Hematite", "Illite+Muscovite", "Hematite_UQ_high_grainsize"]
    src = path.with_suffix(".tif")
    with rasterio.open(
        src, "w", driver="GTiff", height=height, width=width, count=len(names), dtype="float32", crs="EPSG:4326",
        transform=transform, nodata=-9999.0,
    ) as dst:
        for i, name in enumerate(names, 1):
            band = np.full((height, width), -9999.0, dtype="float32")
            if name == "Hematite":
                band[100, 300] = 2.5  # lon -172 + 300*0.5 = -22.0 .. -21.5 ; lat 57 - 100*0.5 = 7.0 .. 6.5
            if name == "Calcite":
                band[100, 300] = 12.0
            if name.endswith("grainsize"):
                band[100, 300] = 99.0
            dst.write(band, i)
            dst.update_tags(i, NETCDF_VARNAME=name)
    rasterio.shutil.copy(src, path, driver="netCDF")


@pytest.mark.skipif(not gdal_has_netcdf(), reason="GDAL without the netCDF driver")
def test_load_emit_grids_from_netcdf_names_fill_and_uncertainty(tmp_path):
    nc = tmp_path / "EMIT_L3_ASA_002.nc"
    make_emit_netcdf(nc, corner_values=False)
    grids = load_emit_grids(nc)
    assert set(grids) == {"calcite", "hematite", "illite_muscovite"}  # the _UQ_ variable is skipped
    out = sample_source(EMIT, grids, 6.8, -21.8)
    assert out["status"] == "ok"
    assert out["values"]["hematite"] == 2.5 and out["values"]["calcite"] == 12.0
    assert out["values"]["illite_muscovite"] is None  # -9999 fill is not a value
    assert out["summary"].startswith("Mostly calcite (12.0%)")
    # a cell that EMIT did not observe, and a latitude beyond 52 degrees
    assert sample_source(EMIT, grids, 20.0, 40.0)["status"] == "no_data"
    assert sample_source(EMIT, grids, 60.0, 40.0)["status"] == "outside_coverage"


@pytest.mark.skipif(not gdal_has_netcdf(), reason="GDAL without the netCDF driver")
def test_load_emit_grids_corner_convention_shifts_half_a_cell(tmp_path):
    nc = tmp_path / "EMIT_corner.nc"
    make_emit_netcdf(nc, corner_values=True)
    auto = load_emit_grids(nc)["hematite"]
    forced_centre = load_emit_grids(nc, corner=False)["hematite"]
    # auto-detection sees multiples of 0.5 and treats them as corners: the grid moves by half a cell
    assert auto.west == pytest.approx(forced_centre.west + 0.25)
    assert auto.north == pytest.approx(forced_centre.north - 0.25)


def test_load_emit_grids_reports_every_backend_when_it_fails(tmp_path):
    bad = tmp_path / "not_netcdf.nc"
    bad.write_bytes(b"this is not a netCDF file")
    with pytest.raises(RuntimeError) as err:
        load_emit_grids(bad)
    assert "GDAL" in str(err.value) and "xarray" in str(err.value)


# --- Enrichment keeps what it is not asked to touch -----------------------------------------------


def test_enrich_twice_with_different_sources_keeps_the_first_blocks():
    universe = {
        "metadata": {"datasets": [], "citations": [], "not_modelled": [{"item": "mineralogy (spectral)", "note": "x"}]},
        "targets": [
            {"id": "m1", "body": "Mars", "lat": 10.0, "lon": 20.0, "analogs": [{"id": "e1", "lat": 30.0, "lon": 40.0}]},
        ],
    }
    tes = {v.key: Grid_from_global(np.full((8, 16), 0.1)) for v in TES.vars}
    first, _ = enrich_universe(universe, tes=tes)
    emit = {v.key: Grid_from_global(np.full((8, 16), 1.5), lat=52.0) for v in EMIT.vars}
    second, counts = enrich_universe(first, emit=emit)
    assert second["targets"][0]["mineralogy"] == first["targets"][0]["mineralogy"]  # untouched by the EMIT pass
    assert second["targets"][0]["analogs"][0]["mineralogy"]["status"] == "ok"
    assert counts == {"emit_l3asa": {"ok": 1}}
    meta = second["metadata"]["mineralogy"]
    assert meta["scored"] is False and set(meta["sources"]) == {"tes_bandfield2002", "emit_l3asa"}
    assert "not scored" in second["metadata"]["not_modelled"][0]["note"]
    assert len(second["metadata"]["datasets"]) == 2 and len(second["metadata"]["citations"]) == 2


def Grid_from_global(data, lat=90.0):
    from pipeline.minerals import Grid

    return Grid(data, west=0.0, east=360.0, north=lat, south=-lat)


def test_enrich_changes_only_mineralogy_and_the_listed_metadata():
    """Every other field of the universe, scores included, must come out identical."""
    import copy
    import json

    universe = {
        "metadata": {
            "version": "2.0.0",
            "datasets": [{"name": "x", "source": "y", "url": None}],
            "citations": ["c"],
            "not_modelled": [{"item": "mineralogy (spectral)", "note": "old"}, {"item": "biology", "note": "keep"}],
            "scoring_policy": {"earth_missing_score": 0.0},
        },
        "mission_presets": {"p": {"weights": {"topography": 1.0}}},
        "targets": [
            {
                "id": "m1", "body": "Mars", "lat": 10.0, "lon": 20.0, "features": {"mean_slope_deg": 1.5},
                "analogs": [{"id": "e1", "lat": 30.0, "lon": 40.0, "sub_scores": {"topography": 0.9, "ice": None},
                             "msi_by_preset": {"p": 0.81}, "mismatches": [{"feature": "geo_class", "z_diff": None}]}],
            },
            {
                "id": "l1", "body": "Moon", "lat": -85.0, "lon": 10.0, "features": {"mean_slope_deg": 9.0},
                "analogs": [{"id": "e2", "lat": 60.0, "lon": 40.0, "sub_scores": {"topography": 0.5}, "msi_by_preset": {"p": 0.5}, "mismatches": []}],
            },
        ],
    }
    before = copy.deepcopy(universe)
    tes = {v.key: Grid_from_global(np.full((8, 16), 0.1)) for v in TES.vars}
    kag = {v.key: Grid_from_global(np.full((8, 16), 0.2), lat=50.0) for v in KAGUYA.vars}
    emit = {v.key: Grid_from_global(np.full((8, 16), 1.5), lat=52.0) for v in EMIT.vars}
    out, _ = enrich_universe(universe, kaguya=kag, tes=tes, emit=emit)
    assert universe == before  # the input is not modified

    def stripped(u):
        u = json.loads(json.dumps(u))
        u["metadata"].pop("mineralogy", None)
        for k in ("datasets", "citations", "not_modelled"):
            u["metadata"].pop(k)
        for t in u["targets"]:
            t.pop("mineralogy", None)
            for a in t["analogs"]:
                a.pop("mineralogy", None)
        return u

    ref = stripped(before)
    ref["metadata"].pop("datasets", None)
    assert stripped(out) == {**ref, "metadata": {k: v for k, v in ref["metadata"].items() if k not in ("datasets", "citations", "not_modelled")}}
    # the unrelated not_modelled item is kept as it was, the mineralogy one is rewritten
    notes = {i["item"]: i["note"] for i in out["metadata"]["not_modelled"]}
    assert notes["biology"] == "keep" and "not scored" in notes["mineralogy (spectral)"]
    # the polar Moon target is outside Kaguya, and the 60N analog is outside EMIT
    assert out["targets"][1]["mineralogy"]["status"] == "outside_coverage"
    assert out["targets"][1]["analogs"][0]["mineralogy"]["status"] == "outside_coverage"
