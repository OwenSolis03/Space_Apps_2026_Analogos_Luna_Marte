"""Definición de blancos curados y clusters globales para Marte y la Luna (T4)."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import subprocess

os.environ.setdefault("PROJ_IGNORE_CELESTIAL_BODY", "YES")

import matplotlib

matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pyproj import Geod
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from .config import BODY_RADII_M, FEATURE_NAMES, PATCH_RES_M, PATCH_SIZE_KM, YUCA_PROJECT_DIR
from .iau import iau_label, load_gazetteer
from .planet_features import PointSampler, compute_lunar_wac_percentile

CLUSTER_FEATURES: list[str] = [
    "mean_slope_deg",
    "p90_slope_deg",
    "relief_m",
    "hypsometric_integral",
    "detrended_std_m",
    "tri_m",
]
LOG_FEATURES: list[str] = ["relief_m", "detrended_std_m", "tri_m"]
N_CLUSTERS: int = 30
KMEANS_SEED: int = 42
NEIGHBOR_OFFSET_KM: float = 16.0
MIN_OK: dict[str, int] = {"point": 3, "rim": 5}
TARGETS_JSON: Path = Path(__file__).parent / "data" / "targets.json"
AUX_COLS: dict[str, list[str]] = {
    "Mars": ["themis_day", "themis_night", "themis_delta"],
    "Moon": [
        "wac_reflectance",
        "wac_percentile",
        "ice_favorability",
        "diviner_tmax_k",
        "diviner_tavg_k",
        "ice_depth_m",
    ],
}

ALL_AUX_AND_DERIVED_COLS: list[str] = [
    "themis_day",
    "themis_night",
    "themis_delta",
    "wac_reflectance",
    "wac_percentile",
    "ice_favorability",
    "diviner_tmax_k",
    "diviner_tavg_k",
    "ice_depth_m",
    "ice_stable_frac",
]

TARGET_COLUMNS: list[str] = [
    "target_id",
    "type",
    "body",
    "name",
    "category",
    "why",
    "lat",
    "lon",
    "anchor_type",
    "anchor_note",
    "source_url",
    "coord_source_url",
    "status",
    "n_patches",
    "n_ok",
    *FEATURE_NAMES,
    "mean_slope_std",
    *ALL_AUX_AND_DERIVED_COLS,
    "iau_label",
    "iau_nearest",
    "iau_distance_km",
    "iau_link",
    "cluster_rank",
    "cluster_size",
    "cluster_frac",
]


def _is_finite(val: object) -> bool:
    if val is None:
        return False
    try:
        return bool(np.isfinite(float(val)))
    except (TypeError, ValueError):
        return False


def _nanmean32(values: list[object]) -> np.float32:
    arr = np.asarray(
        [float(v) if _is_finite(v) else np.nan for v in values],
        dtype=np.float64,
    )
    valid = arr[np.isfinite(arr)]
    if valid.size == 0:
        return np.float32(np.nan)
    return np.float32(np.mean(valid))


def load_curated(path: Path = TARGETS_JSON) -> list[dict]:
    """Lee y valida `targets.json`. Lanza ValueError indicando el id que falla."""
    with open(path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)

    targets = payload.get("targets")
    if not isinstance(targets, list):
        raise ValueError(f"El archivo {path} debe contener una lista 'targets'.")

    seen_ids: set[str] = set()
    for idx, item in enumerate(targets):
        if not isinstance(item, dict):
            raise ValueError(f"Blanco en índice {idx} no es un objeto JSON.")
        tid = item.get("id")
        if not isinstance(tid, str) or not tid.strip():
            raise ValueError(f"Blanco sin id válido en índice {idx}.")
        if tid in seen_ids:
            raise ValueError(f"id duplicado en targets.json: {tid!r}")
        seen_ids.add(tid)

        body = item.get("body")
        if body not in ("Moon", "Mars"):
            raise ValueError(f"Blanco {tid!r}: body inválido {body!r} (esperado Moon o Mars).")

        lat = item.get("lat")
        lon = item.get("lon")
        if not isinstance(lat, (int, float)) or not math.isfinite(float(lat)) or not (-90.0 <= float(lat) <= 90.0):
            raise ValueError(f"Blanco {tid!r}: lat fuera de [-90, 90]: {lat!r}")
        if not isinstance(lon, (int, float)) or not math.isfinite(float(lon)) or not (-180.0 <= float(lon) <= 180.0):
            raise ValueError(f"Blanco {tid!r}: lon fuera de [-180, 180]: {lon!r}")

        anchor = item.get("anchor")
        if not isinstance(anchor, dict):
            raise ValueError(f"Blanco {tid!r}: falta objeto 'anchor'.")
        atype = anchor.get("type")
        if atype not in ("point", "rim"):
            raise ValueError(f"Blanco {tid!r}: anchor.type inválido {atype!r}.")
        if atype == "rim":
            rad = anchor.get("radius_km")
            if not isinstance(rad, (int, float)) or not math.isfinite(float(rad)) or float(rad) <= 0.0:
                raise ValueError(f"Blanco {tid!r}: anchor rim requiere radius_km > 0 (recibido {rad!r}).")

        for url_key in ("source_url", "coord_source_url"):
            url_val = item.get(url_key)
            if not isinstance(url_val, str) or not url_val.strip():
                raise ValueError(f"Blanco {tid!r}: {url_key} vacío o faltante.")

    return targets


def anchor_points(target: dict) -> list[tuple[float, float]]:
    """Calcula los centros (lat, lon) de los parches del blanco con pyproj.Geod."""
    body = str(target["body"])
    r_m = BODY_RADII_M[body]
    geod = Geod(a=r_m, b=r_m)

    lat0 = float(target["lat"])
    lon0 = ((float(target["lon"]) + 180.0) % 360.0) - 180.0
    anchor = target["anchor"]
    atype = anchor["type"]

    pts: list[tuple[float, float]] = []
    if atype == "point":
        pts.append((lat0, lon0))
        dist_m = NEIGHBOR_OFFSET_KM * 1000.0
        for az in (0.0, 90.0, 180.0, 270.0):
            lon2, lat2, _ = geod.fwd(lon0, lat0, az, dist_m)
            lon2_norm = ((float(lon2) + 180.0) % 360.0) - 180.0
            pts.append((float(lat2), lon2_norm))
    elif atype == "rim":
        dist_m = float(anchor["radius_km"]) * 1000.0
        for az in (0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0):
            lon2, lat2, _ = geod.fwd(lon0, lat0, az, dist_m)
            lon2_norm = ((float(lon2) + 180.0) % 360.0) - 180.0
            pts.append((float(lat2), lon2_norm))
    else:
        raise ValueError(f"Tipo de ancla no soportado: {atype!r}")

    return pts


def aggregate_patches(rows: list[dict | None], anchor_type: str, body: str) -> dict[str, object]:
    """Agrega las filas de PointSampler.sample para un blanco curado."""
    if anchor_type not in MIN_OK:
        raise ValueError(f"Tipo de ancla no soportado: {anchor_type!r}")
    body_norm = body.strip().capitalize()
    if body_norm not in AUX_COLS:
        raise ValueError(f"Cuerpo no soportado: {body!r}")

    n_patches = len(rows)
    valid_rows = [r for r in rows if r is not None]
    n_ok = len(valid_rows)
    nan32 = np.float32(np.nan)

    out: dict[str, object] = {
        "n_patches": int(n_patches),
        "n_ok": int(n_ok),
    }

    if n_ok < MIN_OK[anchor_type]:
        out["status"] = "insufficient_coverage"
        for col in FEATURE_NAMES:
            out[col] = nan32
        out["mean_slope_std"] = nan32
        for col in ALL_AUX_AND_DERIVED_COLS:
            out[col] = nan32
        return out

    out["status"] = "ok"
    for col in FEATURE_NAMES:
        out[col] = _nanmean32([r.get(col) for r in valid_rows])

    slopes = np.asarray(
        [float(r["mean_slope_deg"]) for r in valid_rows if _is_finite(r.get("mean_slope_deg"))],
        dtype=np.float64,
    )
    out["mean_slope_std"] = np.float32(np.std(slopes)) if slopes.size > 0 else nan32

    for col in ALL_AUX_AND_DERIVED_COLS:
        if col in AUX_COLS[body_norm]:
            out[col] = _nanmean32([r.get(col) for r in valid_rows])
        else:
            out[col] = nan32

    if body_norm == "Moon":
        div_rows = [
            r
            for r in valid_rows
            if _is_finite(r.get("diviner_tavg_k")) or _is_finite(r.get("diviner_tmax_k"))
        ]
        if div_rows:
            stable_cnt = sum(1 for r in div_rows if _is_finite(r.get("ice_depth_m")))
            out["ice_stable_frac"] = np.float32(stable_cnt / len(div_rows))
        else:
            out["ice_stable_frac"] = nan32

    return out


def _empty_targets_df() -> pd.DataFrame:
    df = pd.DataFrame(columns=TARGET_COLUMNS)
    return _enforce_target_dtypes(df)


def _enforce_target_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        df = pd.DataFrame({c: pd.Series(dtype="object") for c in TARGET_COLUMNS})
    else:
        df = df.reindex(columns=TARGET_COLUMNS).copy()

    str_cols = [
        "target_id",
        "type",
        "body",
        "name",
        "category",
        "why",
        "anchor_type",
        "anchor_note",
        "source_url",
        "coord_source_url",
        "status",
        "iau_label",
        "iau_nearest",
        "iau_link",
    ]
    for c in str_cols:
        df[c] = df[c].astype("string")

    for c in ("lat", "lon", "iau_distance_km"):
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("float64")

    for c in ("n_patches", "n_ok"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype("int16")

    float32_cols = [*FEATURE_NAMES, "mean_slope_std", *ALL_AUX_AND_DERIVED_COLS]
    for c in float32_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("float32")

    df["cluster_rank"] = pd.to_numeric(df["cluster_rank"], errors="coerce").astype("Int32")
    df["cluster_size"] = pd.to_numeric(df["cluster_size"], errors="coerce").astype("Int32")
    df["cluster_frac"] = pd.to_numeric(df["cluster_frac"], errors="coerce").astype("float32")
    return df


def curated_features(
    targets: list[dict],
    raw_dir: Path,
    derived_dir: Path,
    t3_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Calcula rasgos T1+T2+T3 de los blancos curados promediando sus parches de ancla."""
    moon_pq = t3_dir / "features_moon.parquet"
    wac_ref: np.ndarray | None = None
    if moon_pq.exists():
        moon_df = pd.read_parquet(moon_pq, columns=["wac_reflectance"])
        if "wac_reflectance" in moon_df.columns:
            wac_ref = moon_df["wac_reflectance"].to_numpy(dtype=np.float64)

    target_rows: list[dict[str, object]] = []
    patch_rows: list[dict[str, object]] = []

    for body in ("Moon", "Mars"):
        body_targets = [t for t in targets if t["body"] == body]
        if not body_targets:
            continue

        gaz = load_gazetteer(body, raw_dir)
        radius_km = BODY_RADII_M[body] / 1000.0

        with PointSampler(body, raw_dir=raw_dir, derived_dir=derived_dir) as sampler:
            for target in body_targets:
                tid = str(target["id"])
                anchor = target["anchor"]
                atype = str(anchor["type"])
                pts = anchor_points(target)
                sampled: list[dict | None] = []

                for k_idx, (plat, plon) in enumerate(pts):
                    row = sampler.sample(plat, plon)
                    if row is not None and body == "Moon":
                        wac_val = row.get("wac_reflectance", np.nan)
                        if wac_ref is not None and _is_finite(wac_val):
                            row["wac_percentile"] = np.float32(
                                compute_lunar_wac_percentile(float(wac_val), reference=wac_ref)
                            )
                        else:
                            row["wac_percentile"] = np.float32(np.nan)
                    sampled.append(row)

                    patch_rec: dict[str, object] = {
                        "target_id": tid,
                        "body": body,
                        "k": int(k_idx),
                        "lat": float(plat),
                        "lon": float(plon),
                        "ok": bool(row is not None),
                    }
                    for col in [*FEATURE_NAMES, *ALL_AUX_AND_DERIVED_COLS, "valid_frac"]:
                        if col == "ice_stable_frac":
                            continue
                        patch_rec[col] = np.float32(row[col]) if (row is not None and col in row) else np.float32(np.nan)
                    patch_rows.append(patch_rec)

                agg = aggregate_patches(sampled, anchor_type=atype, body=body)
                iau = iau_label(float(target["lat"]), float(target["lon"]), gaz, radius_km=radius_km)

                t_row: dict[str, object] = {
                    "target_id": tid,
                    "type": "CURATED",
                    "body": body,
                    "name": str(target["name"]),
                    "category": str(target["category"]),
                    "why": str(target["why"]),
                    "lat": float(target["lat"]),
                    "lon": float(target["lon"]),
                    "anchor_type": atype,
                    "anchor_note": str(anchor.get("note", "")),
                    "source_url": str(target["source_url"]),
                    "coord_source_url": str(target["coord_source_url"]),
                    "iau_label": str(iau["display_label"]),
                    "iau_nearest": str(iau["nearest_feature"]),
                    "iau_distance_km": float(iau["distance_km"]),
                    "iau_link": iau["link"],
                    "cluster_rank": pd.NA,
                    "cluster_size": pd.NA,
                    "cluster_frac": np.float32(np.nan),
                    **agg,
                }
                target_rows.append(t_row)

    targets_df = _enforce_target_dtypes(pd.DataFrame(target_rows)) if target_rows else _empty_targets_df()
    patches_df = pd.DataFrame(patch_rows)
    if not patches_df.empty:
        patches_df["target_id"] = patches_df["target_id"].astype("string")
        patches_df["body"] = patches_df["body"].astype("string")
        patches_df["k"] = patches_df["k"].astype("int16")
        patches_df["lat"] = patches_df["lat"].astype("float64")
        patches_df["lon"] = patches_df["lon"].astype("float64")
        patches_df["ok"] = patches_df["ok"].astype("bool")
    return targets_df, patches_df


def _transform_cluster_matrix(df: pd.DataFrame) -> np.ndarray:
    x = df[CLUSTER_FEATURES].to_numpy(dtype=np.float64, copy=True)
    for idx, feat in enumerate(CLUSTER_FEATURES):
        if feat in LOG_FEATURES:
            x[:, idx] = np.log1p(np.maximum(0.0, x[:, idx]))
    return x


def build_clusters(
    df: pd.DataFrame,
    body: str,
    k: int = N_CLUSTERS,
    seed: int = KMEANS_SEED,
    return_labels: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame] | tuple[pd.DataFrame, pd.DataFrame, np.ndarray]:
    """Agrupa parches T3 de `body` con k-means sobre 6 rasgos estandarizados."""
    body_norm = body.strip().capitalize()
    if df.empty:
        raise ValueError(f"DataFrame vacío para clustering de {body_norm}.")
    if k <= 0 or k > len(df):
        raise ValueError(f"k={k} inválido para {len(df)} filas en {body_norm}.")

    work_df = df.reset_index(drop=True).copy()
    if body_norm == "Moon" and "wac_percentile" not in work_df.columns:
        if "wac_reflectance" in work_df.columns:
            work_df["wac_percentile"] = compute_lunar_wac_percentile(work_df["wac_reflectance"])
        else:
            work_df["wac_percentile"] = np.float32(np.nan)

    x_trans = _transform_cluster_matrix(work_df)
    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(x_trans)

    kmeans = KMeans(n_clusters=k, n_init=10, random_state=seed)
    raw_labels = kmeans.fit_predict(x_scaled)

    counts = np.bincount(raw_labels, minlength=k)
    order = sorted(range(k), key=lambda cid: (-int(counts[cid]), int(cid)))

    cid_to_rank = {old_cid: rank for rank, old_cid in enumerate(order, start=1)}
    rank_labels = np.array([cid_to_rank[int(c)] for c in raw_labels], dtype=np.int32)

    centers_trans = scaler.inverse_transform(kmeans.cluster_centers_)
    centers_phys = centers_trans.copy()
    for idx, feat in enumerate(CLUSTER_FEATURES):
        if feat in LOG_FEATURES:
            centers_phys[:, idx] = np.expm1(centers_phys[:, idx])

    n_total = len(work_df)
    rep_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []

    for rank, old_cid in enumerate(order, start=1):
        member_idx = np.flatnonzero(raw_labels == old_cid)
        member_scaled = x_scaled[member_idx]
        center = kmeans.cluster_centers_[old_cid]
        dists = np.linalg.norm(member_scaled - center, axis=1)
        best_pos = int(np.argmin(dists))
        rep_idx = int(member_idx[best_pos])
        rep_dist = float(dists[best_pos])

        c_size = int(member_idx.size)
        c_frac = float(c_size / n_total)

        rep_dict = work_df.iloc[rep_idx].to_dict()
        rep_dict["cluster_rank"] = int(rank)
        rep_dict["cluster_size"] = int(c_size)
        rep_dict["cluster_frac"] = np.float32(c_frac)
        rep_dict["dist_to_centroid"] = np.float32(rep_dist)
        rep_rows.append(rep_dict)

        sum_row: dict[str, object] = {
            "cluster_rank": int(rank),
            "size": int(c_size),
            "frac": np.float32(c_frac),
        }
        sub_df = work_df.iloc[member_idx]
        for idx, feat in enumerate(CLUSTER_FEATURES):
            sum_row[f"{feat}_median"] = np.float32(sub_df[feat].median())
            sum_row[f"centroid_{feat}"] = np.float32(centers_phys[old_cid, idx])
        summary_rows.append(sum_row)

    reps_df = pd.DataFrame(rep_rows)
    summary_df = pd.DataFrame(summary_rows)
    summary_df.attrs["inertia"] = float(kmeans.inertia_)

    if return_labels:
        return reps_df, summary_df, rank_labels
    return reps_df, summary_df


def cluster_targets(
    reps_df: pd.DataFrame,
    summary_df: pd.DataFrame,
    body: str,
    gaz: pd.DataFrame,
) -> pd.DataFrame:
    """Convierte representantes de clusters en blancos con el esquema común."""
    body_norm = body.strip().capitalize()
    radius_km = BODY_RADII_M[body_norm] / 1000.0

    summary_by_rank = summary_df.set_index("cluster_rank")
    rows: list[dict[str, object]] = []

    for _, rep in reps_df.iterrows():
        rank = int(rep["cluster_rank"])
        c_size = int(rep["cluster_size"])
        c_frac = float(rep["cluster_frac"])
        lat = float(rep["lat"])
        lon = float(rep["lon"])

        sum_row = summary_by_rank.loc[rank]
        med_slope = float(sum_row["mean_slope_deg_median"])
        med_relief = float(sum_row["relief_m_median"])
        med_tri = float(sum_row["tri_m_median"])

        iau = iau_label(lat, lon, gaz, radius_km=radius_km)

        rec: dict[str, object] = {
            "target_id": f"{body_norm.lower()}-cluster-{rank:02d}",
            "type": "CLUSTER",
            "body": body_norm,
            "name": str(iau["display_label"]),
            "category": "Global terrain archetype (k-means)",
            "why": (
                f"Archetype covering {c_frac:.1%} of {body_norm}'s 32 km patches: "
                f"median mean slope {med_slope:.1f}°, relief {med_relief:.0f} m, TRI {med_tri:.0f} m."
            ),
            "lat": lat,
            "lon": lon,
            "anchor_type": "patch",
            "anchor_note": "Representative T3 patch closest to the cluster centroid.",
            "source_url": iau["link"],
            "coord_source_url": None,
            "status": "ok",
            "n_patches": 1,
            "n_ok": 1,
            "mean_slope_std": np.float32(0.0),
            "iau_label": str(iau["display_label"]),
            "iau_nearest": str(iau["nearest_feature"]),
            "iau_distance_km": float(iau["distance_km"]),
            "iau_link": iau["link"],
            "cluster_rank": rank,
            "cluster_size": c_size,
            "cluster_frac": np.float32(c_frac),
        }

        for feat in FEATURE_NAMES:
            rec[feat] = np.float32(rep.get(feat, np.nan))

        for aux in ALL_AUX_AND_DERIVED_COLS:
            if aux == "ice_stable_frac":
                if body_norm == "Moon" and (
                    _is_finite(rep.get("diviner_tavg_k")) or _is_finite(rep.get("diviner_tmax_k"))
                ):
                    rec[aux] = np.float32(1.0 if _is_finite(rep.get("ice_depth_m")) else 0.0)
                else:
                    rec[aux] = np.float32(np.nan)
            elif aux in AUX_COLS[body_norm]:
                rec[aux] = np.float32(rep.get(aux, np.nan))
            else:
                rec[aux] = np.float32(np.nan)

        rows.append(rec)

    return _enforce_target_dtypes(pd.DataFrame(rows)) if rows else _empty_targets_df()


def plot_targets_map(
    t3_df: pd.DataFrame,
    labels: np.ndarray,
    targets_df: pd.DataFrame,
    body: str,
    png_path: Path,
) -> Path:
    """Genera mapa scatter de clusters T3, representantes y blancos curados."""
    png_path.parent.mkdir(parents=True, exist_ok=True)
    colors = list(plt.get_cmap("tab20").colors) + list(plt.get_cmap("tab10").colors)
    cmap = mcolors.ListedColormap(colors[:30])

    fig, ax = plt.subplots(figsize=(12, 6))
    if len(t3_df) > 0:
        c_idx = (np.asarray(labels, dtype=np.int32) - 1) % 30
        marker_size = 5.0 if len(t3_df) < 3000 else 1.2
        ax.scatter(
            t3_df["lon"],
            t3_df["lat"],
            c=c_idx,
            cmap=cmap,
            vmin=0,
            vmax=29,
            s=marker_size,
            alpha=0.8,
            linewidths=0,
        )

    sub = targets_df[targets_df["body"] == body]
    clusters_sub = sub[sub["type"] == "CLUSTER"]
    if not clusters_sub.empty:
        ax.scatter(
            clusters_sub["lon"],
            clusters_sub["lat"],
            s=55,
            facecolors="white",
            edgecolors="black",
            linewidths=0.9,
            zorder=4,
            label="Cluster rep.",
        )
        for _, row in clusters_sub.iterrows():
            rank = int(row["cluster_rank"])
            ax.annotate(
                str(rank),
                (float(row["lon"]), float(row["lat"])),
                fontsize=6,
                fontweight="bold",
                ha="center",
                va="center",
                color="black",
                zorder=5,
            )

    curated_sub = sub[sub["type"] == "CURATED"]
    if not curated_sub.empty:
        ok_cur = curated_sub[curated_sub["status"] == "ok"]
        if not ok_cur.empty:
            ax.scatter(
                ok_cur["lon"],
                ok_cur["lat"],
                marker="*",
                s=170,
                c="black",
                edgecolors="white",
                linewidths=0.7,
                zorder=6,
                label="Curated",
            )
            for _, row in ok_cur.iterrows():
                ax.annotate(
                    str(row["target_id"]),
                    (float(row["lon"]), float(row["lat"])),
                    xytext=(4, 4),
                    textcoords="offset points",
                    fontsize=6.5,
                    color="black",
                    bbox={"boxstyle": "round,pad=0.15", "fc": "white", "ec": "none", "alpha": 0.75},
                    zorder=7,
                )

    ax.set_xlim(-180, 180)
    ax.set_ylim(-90, 90)
    ax.set_xlabel("Longitud (°)")
    ax.set_ylabel("Latitud (°)")
    ax.set_title(f"{body} — clusters ({len(clusters_sub)}) y blancos curados ({len(curated_sub)})")
    ax.grid(True, linestyle="--", linewidth=0.4, alpha=0.4)
    if not clusters_sub.empty or not curated_sub.empty:
        ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(png_path, dpi=180)
    plt.close(fig)
    return png_path


def _round_or_none(val: object, digits: int = 4) -> float | None:
    if val is None or pd.isna(val):
        return None
    val_f = float(val)
    if not math.isfinite(val_f):
        return None
    return round(val_f, digits)


def _str_or_none(val: object) -> str | None:
    if val is None or pd.isna(val):
        return None
    s = str(val).strip()
    return s if s else None


def _targets_df_to_json_payload(
    targets_df: pd.DataFrame,
    t3_dir: Path,
    k: int,
    commit: str,
) -> dict[str, object]:
    items: list[dict[str, object]] = []
    for _, row in targets_df.iterrows():
        body = str(row["body"])
        features_obj = {feat: _round_or_none(row[feat], 4) for feat in FEATURE_NAMES}
        aux_keys = (
            ["themis_day", "themis_night", "themis_delta"]
            if body == "Mars"
            else [
                "wac_reflectance",
                "wac_percentile",
                "ice_favorability",
                "diviner_tmax_k",
                "diviner_tavg_k",
                "ice_depth_m",
                "ice_stable_frac",
            ]
        )
        aux_obj = {col: _round_or_none(row[col], 4) for col in aux_keys}

        cluster_obj: dict[str, object] | None = None
        if str(row["type"]) == "CLUSTER":
            cluster_obj = {
                "rank": int(row["cluster_rank"]),
                "size": int(row["cluster_size"]),
                "frac": _round_or_none(row["cluster_frac"], 4),
            }

        items.append(
            {
                "id": str(row["target_id"]),
                "type": str(row["type"]),
                "body": body,
                "name": str(row["name"]),
                "lat": _round_or_none(row["lat"], 4),
                "lon": _round_or_none(row["lon"], 4),
                "category": str(row["category"]),
                "why": str(row["why"]),
                "source_url": _str_or_none(row["source_url"]),
                "coord_source_url": _str_or_none(row["coord_source_url"]),
                "anchor": {
                    "type": str(row["anchor_type"]),
                    "note": str(row["anchor_note"]),
                },
                "status": str(row["status"]),
                "n_patches": int(row["n_patches"]),
                "n_ok": int(row["n_ok"]),
                "mean_slope_std": _round_or_none(row["mean_slope_std"], 4),
                "iau_label": _str_or_none(row["iau_label"]),
                "iau_nearest": _str_or_none(row["iau_nearest"]),
                "iau_distance_km": _round_or_none(row["iau_distance_km"], 4),
                "iau_link": _str_or_none(row["iau_link"]),
                "features": features_obj,
                "aux": aux_obj,
                "cluster": cluster_obj,
            }
        )

    return {
        "metadata": {
            "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
            "t3_run": str(t3_dir),
            "k": int(k),
            "seed": int(KMEANS_SEED),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "commit": commit,
        },
        "targets": items,
    }


def _git_short_commit(code_dir: Path) -> str:
    try:
        res = subprocess.run(
            ["git", "-C", str(code_dir), "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return res.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _print_sanity_checks(targets_df: pd.DataFrame, t3_dfs: dict[str, pd.DataFrame]) -> None:
    print("[CHECKS] Revisión de sentido común (sección 10 de plan_t4.md):")
    cur = targets_df[(targets_df["type"] == "CURATED") & (targets_df["status"] == "ok")]

    if "Mars" in t3_dfs:
        mars_global_med = float(t3_dfs["Mars"]["mean_slope_deg"].median())
        mars_cur = cur[cur["body"] == "Mars"].sort_values("mean_slope_deg")
        top3_ids = list(mars_cur["target_id"].head(3))
        print(f"  Mars mediana global mean_slope_deg = {mars_global_med:.2f}°; top-3 más planos = {top3_ids}")
        for _, r in mars_cur.iterrows():
            print(
                f"    Mars curado {r['target_id']}: mean_slope={float(r['mean_slope_deg']):.2f}°, "
                f"relief={float(r['relief_m']):.1f} m"
            )
        if {"mars-gale-curiosity", "mars-elysium-insight"}.issubset(set(mars_cur["target_id"])):
            gale_rel = float(mars_cur.loc[mars_cur["target_id"] == "mars-gale-curiosity", "relief_m"].iloc[0])
            insight_rel = float(mars_cur.loc[mars_cur["target_id"] == "mars-elysium-insight", "relief_m"].iloc[0])
            print(f"    Gale vs InSight relief_m: {gale_rel:.1f} m vs {insight_rel:.1f} m (esperado Gale > InSight)")

    if "Moon" in t3_dfs:
        moon_global_med = float(t3_dfs["Moon"]["mean_slope_deg"].median())
        moon_cur = cur[cur["body"] == "Moon"].sort_values("mean_slope_deg")
        print(f"  Moon mediana global mean_slope_deg = {moon_global_med:.2f}°:")
        for _, r in moon_cur.iterrows():
            s = float(r["mean_slope_deg"])
            rel_txt = ">=" if s >= moon_global_med else "<"
            print(f"    Moon curado {r['target_id']}: mean_slope={s:.2f}° ({rel_txt} mediana global)")


def run(
    t3_dir: Path,
    out_dir: Path,
    project_dir: Path,
    bodies: list[str],
    k: int = N_CLUSTERS,
    skip_curated: bool = False,
) -> Path:
    """Orquesta extracción de blancos curados, clustering y escritura de salidas T4."""
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = project_dir / "data" / "raw"
    derived_dir = project_dir / "data" / "derived"
    commit = _git_short_commit(Path(__file__).resolve().parent.parent)

    print(f"[T4] t3_dir={t3_dir} out_dir={out_dir} commit={commit}")

    all_target_dfs: list[pd.DataFrame] = []
    patches_df = pd.DataFrame()
    curated_spec_by_id: dict[str, dict] = {}

    if not skip_curated:
        curated_list = [t for t in load_curated() if t["body"] in bodies]
        curated_spec_by_id = {str(t["id"]): t for t in curated_list}
        curated_df, patches_df = curated_features(
            curated_list,
            raw_dir=raw_dir,
            derived_dir=derived_dir,
            t3_dir=t3_dir,
        )
        all_target_dfs.append(curated_df)

        for _, row in curated_df.iterrows():
            tid = str(row["target_id"])
            body = str(row["body"])
            aux_txt = ""
            if body == "Moon" and _is_finite(row["diviner_tavg_k"]):
                aux_txt = f" div_tavg={float(row['diviner_tavg_k']):.1f} K"
            elif body == "Mars" and _is_finite(row["themis_day"]):
                aux_txt = f" themis_day={float(row['themis_day']):.1f}"
            expected_iau = curated_spec_by_id.get(tid, {}).get("anchor", {}).get("iau_feature")
            iau_warn = ""
            if expected_iau and str(row["iau_nearest"]).casefold() != str(expected_iau).casefold():
                iau_warn = f" [WARN expected iau={expected_iau!r}]"
            slope_txt = f"{float(row['mean_slope_deg']):.2f}°" if _is_finite(row["mean_slope_deg"]) else "NaN"
            relief_txt = f"{float(row['relief_m']):.0f} m" if _is_finite(row["relief_m"]) else "NaN"
            print(
                f"[CURADO] {tid}  {row['anchor_type']}  {int(row['n_ok'])}/{int(row['n_patches'])} {row['status']}  "
                f"slope={slope_txt} relief={relief_txt}  "
                f"iau={row['iau_label']} d={float(row['iau_distance_km']):.1f} km{aux_txt}{iau_warn}"
            )

        summary_parts: list[str] = []
        bad_ids: list[str] = []
        for body in bodies:
            b_cur = curated_df[curated_df["body"] == body]
            ok_cnt = int((b_cur["status"] == "ok").sum())
            summary_parts.append(f"{body} {ok_cnt}/{len(b_cur)} ok")
            bad_ids.extend(list(b_cur.loc[b_cur["status"] != "ok", "target_id"]))
        extra = f" (insufficient_coverage: {', '.join(bad_ids)})" if bad_ids else ""
        print(f"[CURADO] resumen: {', '.join(summary_parts)}{extra}")
    else:
        patches_df = pd.DataFrame(
            columns=["target_id", "body", "k", "lat", "lon", "ok", *FEATURE_NAMES, "valid_frac"]
        )

    patches_path = out_dir / "targets_patches.parquet"
    patches_df.to_parquet(patches_path, index=False)

    t3_dfs: dict[str, pd.DataFrame] = {}
    cluster_labels_by_body: dict[str, np.ndarray] = {}

    for body in bodies:
        body_lower = body.lower()
        t3_path = t3_dir / f"features_{body_lower}.parquet"
        if not t3_path.exists():
            raise FileNotFoundError(f"No se encontró salida de T3 para {body}: {t3_path}")
        t3_df = pd.read_parquet(t3_path)
        t3_dfs[body] = t3_df

        reps_df, summary_df, rank_labels = build_clusters(t3_df, body=body, k=k, seed=KMEANS_SEED, return_labels=True)
        cluster_labels_by_body[body] = rank_labels

        summary_path = out_dir / f"clusters_{body_lower}.parquet"
        summary_df.to_parquet(summary_path, index=False)

        gaz = load_gazetteer(body, raw_dir)
        c_targets_df = cluster_targets(reps_df, summary_df, body=body, gaz=gaz)
        all_target_dfs.append(c_targets_df)

        sizes = summary_df["size"].to_numpy(dtype=np.int64)
        inertia = float(summary_df.attrs.get("inertia", float("nan")))
        print(
            f"[CLUSTER] {body}: N={len(t3_df):,}  k={k}  "
            f"tamaño min/mediana/max = {int(sizes.min())}/{int(np.median(sizes))}/{int(sizes.max())}  "
            f"inercia={inertia:.1f}"
        )
        sum_by_rank = summary_df.set_index("cluster_rank")
        for _, crow in c_targets_df.iterrows():
            rank = int(crow["cluster_rank"])
            srow = sum_by_rank.loc[rank]
            print(
                f"[CLUSTER] {body} #{rank:02d}  frac={float(crow['cluster_frac']):.1%}  "
                f"rep=({float(crow['lat']):.2f}, {float(crow['lon']):.2f})  "
                f"slope_med={float(srow['mean_slope_deg_median']):.2f}°  "
                f"relief_med={float(srow['relief_m_median']):.0f} m  -> {crow['name']}"
            )

    non_empty = [d for d in all_target_dfs if not d.empty]
    targets_df = _enforce_target_dtypes(pd.concat(non_empty, ignore_index=True)) if non_empty else _empty_targets_df()

    targets_parquet = out_dir / "targets.parquet"
    targets_df.to_parquet(targets_parquet, index=False)

    targets_json_path = out_dir / "targets.json"
    json_payload = _targets_df_to_json_payload(targets_df, t3_dir=t3_dir, k=k, commit=commit)
    with open(targets_json_path, "w", encoding="utf-8") as fh:
        json.dump(json_payload, fh, indent=2, ensure_ascii=False)

    for body in bodies:
        plot_targets_map(
            t3_dfs[body],
            cluster_labels_by_body[body],
            targets_df,
            body=body,
            png_path=out_dir / f"map_targets_{body.lower()}.png",
        )

    if not skip_curated:
        _print_sanity_checks(targets_df, t3_dfs)

    n_cur = int((targets_df["type"] == "CURATED").sum())
    n_clu = int((targets_df["type"] == "CLUSTER").sum())
    print(f"[OK] targets.parquet: {len(targets_df)} blancos ({n_cur} curados + {n_clu} clusters) -> {targets_parquet}")
    return targets_parquet


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extrae blancos curados y clusters globales de Marte y la Luna (T4)."
    )
    parser.add_argument("--t3-dir", type=Path, required=True, help="Directorio con salidas de T3 (features_*.parquet).")
    parser.add_argument("--out-dir", type=Path, required=True, help="Directorio de salida para T4.")
    parser.add_argument("--project-dir", type=Path, default=YUCA_PROJECT_DIR, help="Raíz de datos en Yuca.")
    parser.add_argument("--body", choices=["Mars", "Moon", "all"], default="all", help="Cuerpo a procesar.")
    parser.add_argument("--k", type=int, default=N_CLUSTERS, help="Número de clusters k-means por cuerpo.")
    parser.add_argument("--skip-curated", action="store_true", help="Omite extracción de blancos curados.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    bodies = ["Mars", "Moon"] if args.body == "all" else [args.body]
    run(
        t3_dir=args.t3_dir,
        out_dir=args.out_dir,
        project_dir=args.project_dir,
        bodies=bodies,
        k=args.k,
        skip_curated=args.skip_curated,
    )


if __name__ == "__main__":
    main()
