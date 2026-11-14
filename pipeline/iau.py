"""Utilidades de nomenclatura IAU/USGS reutilizables para el pipeline v2."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

IAU_SHP: dict[str, str] = {
    "Mars": "nomenclature/MARS_nomenclature_center_pts.shp",
    "Moon": "nomenclature/MOON_nomenclature_center_pts.shp",
}


def _normalize_https_link(value: object) -> str | None:
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    if text.startswith("http://"):
        return "https://" + text[len("http://") :]
    return text


def _normalize_gazetteer_df(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza columnas, longitudes [-180, 180] y enlaces HTTPS del gacetero IAU."""
    if raw_df.empty:
        return pd.DataFrame(columns=["name", "type", "diameter_km", "lat", "lon", "link"])

    cols_lower = {c.lower(): c for c in raw_df.columns}

    def _col(candidates: tuple[str, ...], default: object = None) -> pd.Series:
        for cand in candidates:
            if cand in cols_lower:
                return raw_df[cols_lower[cand]]
        return pd.Series([default] * len(raw_df), index=raw_df.index)

    names = _col(("name", "clean_name"), "").fillna("").astype(str).str.strip()
    if "clean_name" in cols_lower:
        clean_names = raw_df[cols_lower["clean_name"]].fillna("").astype(str).str.strip()
        names = names.where(names != "", clean_names)

    types = _col(("type",), "Feature").fillna("Feature").astype(str).str.strip()
    types = types.where(types != "", "Feature")

    diam = pd.to_numeric(_col(("diameter_km", "diameter"), 0.0), errors="coerce").fillna(0.0)
    lat = pd.to_numeric(_col(("center_lat", "lat"), np.nan), errors="coerce")
    lon_raw = pd.to_numeric(_col(("center_lon", "lon"), np.nan), errors="coerce")
    lon = ((lon_raw + 180.0) % 360.0) - 180.0
    links = _col(("link",), None).map(_normalize_https_link)

    out = pd.DataFrame(
        {
            "name": names,
            "type": types,
            "diameter_km": diam.astype(np.float64),
            "lat": lat.astype(np.float64),
            "lon": lon.astype(np.float64),
            "link": links,
        }
    )
    valid = (out["name"] != "") & np.isfinite(out["lat"]) & np.isfinite(out["lon"])
    return out.loc[valid].reset_index(drop=True)


def load_gazetteer(body: str, raw_dir: Path) -> pd.DataFrame:
    """Lee el gacetero IAU con geopandas y devuelve un DataFrame limpio."""
    body_norm = body.strip().capitalize()
    if body_norm not in IAU_SHP:
        raise ValueError(f"Cuerpo no soportado para gacetero IAU: {body!r}")

    shp_path = raw_dir / IAU_SHP[body_norm]
    if not shp_path.exists():
        raise FileNotFoundError(f"No se encontró el gacetero IAU de {body_norm}: {shp_path}")

    gdf = gpd.read_file(shp_path)
    return _normalize_gazetteer_df(pd.DataFrame(gdf.drop(columns=["geometry"], errors="ignore")))


def haversine_km(
    lat1: float | np.ndarray,
    lon1: float | np.ndarray,
    lat2: float | np.ndarray,
    lon2: float | np.ndarray,
    radius_km: float,
) -> np.ndarray:
    """Calcula distancia haversine en kilómetros sobre una esfera de radio `radius_km`."""
    lat1_arr = np.asarray(lat1, dtype=np.float64)
    lon1_arr = np.asarray(lon1, dtype=np.float64)
    lat2_arr = np.asarray(lat2, dtype=np.float64)
    lon2_arr = np.asarray(lon2, dtype=np.float64)

    p1 = np.radians(lat1_arr)
    p2 = np.radians(lat2_arr)
    dp = np.radians(lat2_arr - lat1_arr)
    dl = np.radians(((lon2_arr - lon1_arr + 180.0) % 360.0) - 180.0)

    a = np.sin(dp / 2.0) ** 2 + np.cos(p1) * np.cos(p2) * (np.sin(dl / 2.0) ** 2)
    return 2.0 * float(radius_km) * np.arctan2(np.sqrt(a), np.sqrt(np.maximum(0.0, 1.0 - a)))


def iau_label(
    lat: float,
    lon: float,
    gaz: pd.DataFrame,
    radius_km: float,
    near_km: float = 80.0,
    major_diam_km: float = 30.0,
) -> dict[str, object]:
    """Asigna etiqueta IAU más cercana y punto regional mayor (>= 30 km) para (lat, lon)."""
    if gaz.empty:
        raise ValueError("El gacetero IAU está vacío.")

    dists = haversine_km(
        float(lat),
        float(lon),
        gaz["lat"].to_numpy(dtype=np.float64),
        gaz["lon"].to_numpy(dtype=np.float64),
        radius_km,
    )
    idx_near = int(np.argmin(dists))
    dn = float(dists[idx_near])
    near_row = gaz.iloc[idx_near]

    diams = gaz["diameter_km"].to_numpy(dtype=np.float64)
    major_mask = diams >= float(major_diam_km)
    if np.any(major_mask):
        major_gaz = gaz.iloc[major_mask]
        dists_major = dists[major_mask]
    else:
        major_gaz = gaz
        dists_major = dists

    idx_reg = int(np.argmin(dists_major))
    dr = float(dists_major[idx_reg])
    reg_row = major_gaz.iloc[idx_reg]

    if dn < near_km:
        display_label = f"{near_row['name']} ({near_row['type']})"
        link = _normalize_https_link(near_row.get("link"))
    else:
        display_label = f"Near {reg_row['name']} ({reg_row['type']})"
        link = _normalize_https_link(reg_row.get("link"))

    return {
        "nearest_feature": str(near_row["name"]),
        "feature_type": str(near_row["type"]),
        "distance_km": round(dn, 1),
        "regional_landmark": str(reg_row["name"]),
        "regional_type": str(reg_row["type"]),
        "regional_distance_km": round(dr, 1),
        "display_label": display_label,
        "link": link,
    }


def find_feature(gaz: pd.DataFrame, name: str) -> pd.Series:
    """Busca un rasgo por nombre exacto (sin distinguir mayúsculas)."""
    target = name.strip().casefold()
    matches = gaz[gaz["name"].astype(str).str.strip().str.casefold() == target]
    if matches.empty:
        raise KeyError(f"Rasgo IAU no encontrado: {name!r}")
    return matches.iloc[0]
