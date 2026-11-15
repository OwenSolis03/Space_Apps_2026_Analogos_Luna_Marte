"""Synthetic unit tests for pipeline/targets.py (T4 target curation, anchors, and clustering)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pipeline.config import BODY_RADII_M
from pipeline.iau import haversine_km
from pipeline.targets import (
    CLUSTER_FEATURES,
    TARGETS_JSON,
    aggregate_patches,
    anchor_points,
    build_clusters,
    cluster_targets,
    load_curated,
)


def test_load_curated_real_file() -> None:
    """Validates real data/targets.json without reading large raster files."""
    targets = load_curated(TARGETS_JSON)
    moon = [t for t in targets if t["body"] == "Moon"]
    mars = [t for t in targets if t["body"] == "Mars"]
    assert len(moon) >= 6
    assert len(mars) >= 6

    ids = [t["id"] for t in targets]
    assert len(ids) == len(set(ids))

    for t in targets:
        assert isinstance(t["source_url"], str) and t["source_url"].strip()
        assert isinstance(t["coord_source_url"], str) and t["coord_source_url"].strip()
        assert -90.0 <= float(t["lat"]) <= 90.0
        assert -180.0 <= float(t["lon"]) <= 180.0
        if t["anchor"]["type"] == "rim":
            assert float(t["anchor"]["radius_km"]) > 0.0


def test_load_curated_rejects_bad(tmp_path: Path) -> None:
    """A targets.json entry with latitude out of range raises ValueError citing the target id."""
    bad_file = tmp_path / "bad_targets.json"
    bad_file.write_text(
        json.dumps(
            {
                "targets": [
                    {
                        "id": "mars-bad-lat",
                        "body": "Mars",
                        "name": "Bad",
                        "category": "Test",
                        "why": "Test",
                        "lat": 95.0,
                        "lon": 10.0,
                        "anchor": {"type": "point", "note": "bad"},
                        "source_url": "https://example.org",
                        "coord_source_url": "https://example.org",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="mars-bad-lat"):
        load_curated(bad_file)


def test_anchor_points_point() -> None:
    """Point anchor generates 5 sample points; the 4 neighbors sit at 16.0 km (±0.01) from center."""
    target = {
        "id": "mars-test-point",
        "body": "Mars",
        "lat": 18.4447,
        "lon": 77.4508,
        "anchor": {"type": "point"},
    }
    pts = anchor_points(target)
    assert len(pts) == 5
    lat0, lon0 = pts[0]
    r_km = BODY_RADII_M["Mars"] / 1000.0
    for lat_n, lon_n in pts[1:]:
        d = float(haversine_km(lat0, lon0, lat_n, lon_n, r_km))
        assert abs(d - 16.0) <= 0.01


def test_anchor_points_rim_near_pole() -> None:
    """Rim anchor for Haworth yields 8 rim points at 25.71 km (±0.01) with longitude in [-180, 180]."""
    target = {
        "id": "moon-a3-haworth",
        "body": "Moon",
        "lat": -87.45,
        "lon": -5.17,
        "anchor": {"type": "rim", "radius_km": 25.71},
    }
    pts = anchor_points(target)
    assert len(pts) == 8
    r_km = BODY_RADII_M["Moon"] / 1000.0
    for lat_p, lon_p in pts:
        assert -180.0 <= lon_p <= 180.0
        d = float(haversine_km(-87.45, -5.17, lat_p, lon_p, r_km))
        assert abs(d - 25.71) <= 0.01


def test_aggregate_min_ok() -> None:
    """Rim with 4/8 valid -> insufficient_coverage and NaN; with 5/8 -> ok and valid mean slope."""
    def _row(slope: float) -> dict[str, object]:
        return {
            "mean_slope_deg": np.float32(slope),
            "p90_slope_deg": np.float32(slope * 1.5),
            "relief_m": np.float32(100.0),
            "hypsometric_integral": np.float32(0.5),
            "detrended_std_m": np.float32(10.0),
            "tri_m": np.float32(20.0),
            "mean_elev_m": np.float32(-1000.0),
            "themis_day": np.float32(120.0),
            "themis_night": np.float32(80.0),
            "themis_delta": np.float32(40.0),
        }

    bad = aggregate_patches([_row(2.0), _row(4.0), _row(6.0), _row(8.0), None, None, None, None], "rim", "Mars")
    assert bad["status"] == "insufficient_coverage"
    assert bad["n_ok"] == 4
    assert bad["n_patches"] == 8
    assert np.isnan(float(bad["mean_slope_deg"]))

    good = aggregate_patches([_row(2.0), _row(4.0), _row(6.0), _row(8.0), _row(10.0), None, None, None], "rim", "Mars")
    assert good["status"] == "ok"
    assert good["n_ok"] == 5
    assert abs(float(good["mean_slope_deg"]) - 6.0) < 1e-5
    assert abs(float(good["themis_delta"]) - 40.0) < 1e-5
    assert np.isnan(float(good["wac_reflectance"]))


def test_aggregate_ice_stable_frac() -> None:
    """4 patches with Diviner coverage and 1 with finite ice_depth_m yield ice_stable_frac == 0.25."""
    def _moon_row(depth: float) -> dict[str, object]:
        return {
            "mean_slope_deg": np.float32(5.0),
            "p90_slope_deg": np.float32(9.0),
            "relief_m": np.float32(300.0),
            "hypsometric_integral": np.float32(0.5),
            "detrended_std_m": np.float32(15.0),
            "tri_m": np.float32(25.0),
            "mean_elev_m": np.float32(0.0),
            "wac_reflectance": np.float32(60.0),
            "wac_percentile": np.float32(0.4),
            "ice_favorability": np.float32(0.8),
            "diviner_tmax_k": np.float32(110.0),
            "diviner_tavg_k": np.float32(55.0),
            "ice_depth_m": np.float32(depth),
        }

    rows = [_moon_row(0.35), _moon_row(np.nan), _moon_row(np.nan), _moon_row(np.nan), None]
    agg = aggregate_patches(rows, anchor_type="point", body="Moon")
    assert agg["status"] == "ok"
    assert abs(float(agg["ice_stable_frac"]) - 0.25) < 1e-6
    assert abs(float(agg["ice_depth_m"]) - 0.35) < 1e-5


def test_build_clusters_blobs() -> None:
    """3 separate Gaussian blobs yield 3 distinct, deterministic real patch representatives."""
    rng = np.random.default_rng(123)
    centers = [
        (1.0, 2.0, 20.0, 0.2, 2.0, 4.0),
        (12.0, 20.0, 900.0, 0.5, 45.0, 90.0),
        (30.0, 45.0, 5000.0, 0.8, 300.0, 600.0),
    ]
    sizes = [130, 100, 70]
    rows: list[dict[str, object]] = []
    for blob_id, (c, n) in enumerate(zip(centers, sizes)):
        for j in range(n):
            vals = np.maximum(0.05, np.array(c) * (1.0 + rng.normal(0.0, 0.03, size=len(c))))
            vals[3] = float(np.clip(vals[3], 0.05, 0.95))
            rec = {feat: np.float32(v) for feat, v in zip(CLUSTER_FEATURES, vals)}
            rec["mean_elev_m"] = np.float32(0.0)
            rec["body"] = "Mars"
            rec["lat"] = float(blob_id * 20.0 + j * 0.01)
            rec["lon"] = float(blob_id * 30.0 + j * 0.01)
            rec["themis_day"] = np.float32(150.0)
            rec["themis_night"] = np.float32(100.0)
            rec["themis_delta"] = np.float32(50.0)
            rec["valid_frac"] = np.float32(1.0)
            rec["blob_id"] = blob_id
            rows.append(rec)

    df = pd.DataFrame(rows)
    reps1, sum1 = build_clusters(df, body="Mars", k=3, seed=42)
    reps2, sum2 = build_clusters(df, body="Mars", k=3, seed=42)

    assert len(reps1) == 3
    assert int(reps1["cluster_size"].sum()) == 300
    assert list(reps1["cluster_rank"]) == [1, 2, 3]
    assert list(reps1["cluster_size"]) == sorted(list(reps1["cluster_size"]), reverse=True)

    # Each medoid representative exists exactly in the input DataFrame and covers a different cluster.
    input_coords = set(zip(df["lat"], df["lon"]))
    rep_coords = list(zip(reps1["lat"], reps1["lon"]))
    for coord in rep_coords:
        assert coord in input_coords
    assert len(set(reps1["blob_id"])) == 3

    # Deterministic reproducibility under identical seed.
    assert list(reps1["lat"]) == list(reps2["lat"])
    assert list(reps1["lon"]) == list(reps2["lon"])
    assert np.allclose(sum1["size"].to_numpy(), sum2["size"].to_numpy())


def test_cluster_targets_schema() -> None:
    """cluster_targets produces formatted id mars-cluster-01, type CLUSTER, and why citing percentage."""
    df = pd.DataFrame(
        [
            {
                "body": "Mars",
                "lat": 10.0,
                "lon": 20.0,
                "mean_slope_deg": np.float32(2.0),
                "p90_slope_deg": np.float32(4.0),
                "relief_m": np.float32(120.0),
                "hypsometric_integral": np.float32(0.5),
                "detrended_std_m": np.float32(15.0),
                "tri_m": np.float32(25.0),
                "mean_elev_m": np.float32(-500.0),
                "themis_day": np.float32(170.0),
                "themis_night": np.float32(90.0),
                "themis_delta": np.float32(80.0),
                "valid_frac": np.float32(1.0),
            }
            for _ in range(10)
        ]
    )
    reps_df, summary_df = build_clusters(df, body="Mars", k=1, seed=42)
    gaz = pd.DataFrame(
        [
            {
                "name": "Jezero",
                "type": "Crater",
                "diameter_km": 49.0,
                "lat": 10.0,
                "lon": 20.0,
                "link": "https://planetarynames.wr.usgs.gov/Feature/15499",
            }
        ]
    )
    ct = cluster_targets(reps_df, summary_df, body="Mars", gaz=gaz)
    assert len(ct) == 1
    row = ct.iloc[0]
    assert row["target_id"] == "mars-cluster-01"
    assert row["type"] == "CLUSTER"
    assert "100.0%" in str(row["why"])
    assert row["name"] == "Jezero (Crater)"
    assert row["status"] == "ok"

