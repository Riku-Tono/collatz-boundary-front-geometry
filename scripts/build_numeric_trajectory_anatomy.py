from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageColor, ImageDraw, ImageFont


ROOT = Path(r"C:\Users\yauki\Documents\Codex\2026-07-01\csv-collatz-state-band-boundary-front")
OUT = ROOT / "outputs" / "numeric_trajectory_anatomy"
SRC_DIR = Path(r"C:\Users\yauki\Documents\design\collatz\boundary-front geometry\boundary-front-geometry\csv")
STAGE_CSV = SRC_DIR / "band_stage_boundary_detail.csv"
EVENT_CSV = SRC_DIR / "miss_and_control_event_detail.csv"

MAX_CLUSTER_STEPS = 6
N_CLUSTERS = 8


def clean_text(value: object) -> str:
    if pd.isna(value):
        return "NA"
    text = str(value).strip()
    return text if text else "NA"


def seq(values: list[object]) -> str:
    out = []
    for value in values:
        if pd.isna(value):
            out.append("NA")
        elif isinstance(value, float) and value.is_integer():
            out.append(str(int(value)))
        else:
            out.append(str(value))
    return " -> ".join(out)


def to_float_series(values: pd.Series) -> pd.Series:
    return pd.to_numeric(values, errors="coerce")


def q(series: pd.Series, quantile: float) -> float:
    s = to_float_series(series).dropna()
    return float(s.quantile(quantile)) if len(s) else np.nan


def median(series: pd.Series) -> float:
    s = to_float_series(series).dropna()
    return float(s.median()) if len(s) else np.nan


def finite(value: float, default: float = 0.0) -> float:
    return float(value) if pd.notna(value) and np.isfinite(value) else default


def font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def blend_hex(c1: str, c2: str, t: float) -> tuple[int, int, int]:
    a = np.array(ImageColor.getrgb(c1), dtype=float)
    b = np.array(ImageColor.getrgb(c2), dtype=float)
    return tuple(np.round(a * (1 - t) + b * t).astype(int))


def prepare_stage_rows() -> pd.DataFrame:
    df = pd.read_csv(STAGE_CSV)
    required = [
        "sample_id",
        "trajectory_id",
        "band",
        "first_entry_index",
        "last_before_R",
        "last_after_R",
        "boundary_k_num",
        "last_before_exit_distance",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required stage columns: {missing}")

    out = df[required].copy()
    out = out.rename(
        columns={
            "last_before_R": "R_before",
            "last_after_R": "R_after",
            "boundary_k_num": "transition_k",
            "last_before_exit_distance": "exit_distance",
        }
    )
    out["band"] = out["band"].map(clean_text)
    for col in ["R_before", "R_after", "transition_k", "exit_distance", "first_entry_index"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out["R_drop"] = out["R_before"] - out["R_after"]
    out["remaining_K_before"] = out["R_before"]
    out = out.sort_values(["sample_id", "trajectory_id", "first_entry_index", "band"], kind="mergesort")
    out["step_index"] = out.groupby(["sample_id", "trajectory_id"]).cumcount()
    return out


def event_labels() -> pd.DataFrame:
    events = pd.read_csv(EVENT_CSV)
    if "miss_event" in events.columns:
        miss_mask = events["miss_event"].astype(str).isin(["1", "True", "true"])
    elif "near_behavior" in events.columns:
        miss_mask = events["near_behavior"].astype(str).eq("miss")
    else:
        miss_mask = pd.Series(False, index=events.index)
    if "group" in events.columns:
        control_mask = events["group"].astype(str).str.contains("control", case=False, na=False) & ~miss_mask
    else:
        control_mask = ~miss_mask
    events = events.assign(_miss=miss_mask.astype(int), _control=control_mask.astype(int))
    return (
        events.groupby(["sample_id", "trajectory_id"], dropna=False)[["_miss", "_control"]]
        .sum()
        .rename(columns={"_miss": "miss_count", "_control": "control_count"})
        .reset_index()
    )


def add_labels(df: pd.DataFrame) -> pd.DataFrame:
    labels = event_labels()
    out = df.merge(labels, on=["sample_id", "trajectory_id"], how="left")
    out[["miss_count", "control_count"]] = out[["miss_count", "control_count"]].fillna(0).astype(int)
    out["contains_miss"] = out["miss_count"] > 0
    out["contains_control"] = out["control_count"] > 0
    return out


def build_numeric_trajectory_table(stage: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (sample_id, trajectory_id), sub in stage.groupby(["sample_id", "trajectory_id"], sort=False):
        sub = sub.sort_values("step_index")
        rdrop = sub["R_drop"]
        k = sub["transition_k"]
        ed = sub["exit_distance"]
        rows.append(
            {
                "sample_id": sample_id,
                "trajectory_id": trajectory_id,
                "n_steps": int(len(sub)),
                "contains_miss": bool(sub["contains_miss"].max()),
                "contains_control": bool(sub["contains_control"].max()),
                "R_before_sequence": seq(sub["R_before"].tolist()),
                "R_after_sequence": seq(sub["R_after"].tolist()),
                "R_drop_sequence": seq(rdrop.tolist()),
                "transition_k_sequence": seq(k.tolist()),
                "exit_distance_sequence": seq(ed.tolist()),
                "remaining_K_before_sequence": seq(sub["remaining_K_before"].tolist()),
                "start_R": finite(sub["R_before"].iloc[0], np.nan),
                "end_R": finite(sub["R_after"].iloc[-1], np.nan),
                "total_R_drop": finite(rdrop.sum(), np.nan),
                "mean_R_drop": finite(rdrop.mean(), np.nan),
                "max_R_drop": finite(rdrop.max(), np.nan),
                "mean_k": finite(k.mean(), np.nan),
                "max_k": finite(k.max(), np.nan),
                "mean_exit_distance": finite(ed.mean(), np.nan),
                "min_exit_distance": finite(ed.min(), np.nan),
                "max_exit_distance": finite(ed.max(), np.nan),
            }
        )
    return pd.DataFrame(rows)


def build_aligned_paths(stage: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (sample_id, trajectory_id), sub in stage.groupby(["sample_id", "trajectory_id"], sort=False):
        sub = sub.sort_values("step_index").reset_index(drop=True)
        n = len(sub)
        for i, r in sub.iterrows():
            rows.append(
                {
                    "sample_id": sample_id,
                    "trajectory_id": trajectory_id,
                    "reverse_step_index": i - (n - 1),
                    "contains_miss": bool(r["contains_miss"]),
                    "contains_control": bool(r["contains_control"]),
                    "band": r["band"],
                    "R_before": r["R_before"],
                    "R_after": r["R_after"],
                    "R_drop": r["R_drop"],
                    "transition_k": r["transition_k"],
                    "exit_distance": r["exit_distance"],
                    "remaining_K_before": r["remaining_K_before"],
                }
            )
    return pd.DataFrame(rows)


def group_name(row: pd.Series) -> str:
    if bool(row["contains_miss"]):
        return "miss"
    if bool(row["contains_control"]):
        return "control"
    return "other"


def build_numeric_summary(aligned: pd.DataFrame) -> pd.DataFrame:
    work = aligned.copy()
    work["group"] = work.apply(group_name, axis=1)
    rows = []
    for (rev, grp), sub in work.groupby(["reverse_step_index", "group"], sort=True):
        rows.append(
            {
                "reverse_step_index": int(rev),
                "group": grp,
                "count": int(len(sub)),
                "median_R_before": median(sub["R_before"]),
                "q25_R_before": q(sub["R_before"], 0.25),
                "q75_R_before": q(sub["R_before"], 0.75),
                "median_R_drop": median(sub["R_drop"]),
                "q25_R_drop": q(sub["R_drop"], 0.25),
                "q75_R_drop": q(sub["R_drop"], 0.75),
                "median_k": median(sub["transition_k"]),
                "q25_k": q(sub["transition_k"], 0.25),
                "q75_k": q(sub["transition_k"], 0.75),
                "median_exit_distance": median(sub["exit_distance"]),
                "q25_exit_distance": q(sub["exit_distance"], 0.25),
                "q75_exit_distance": q(sub["exit_distance"], 0.75),
            }
        )
    return pd.DataFrame(rows).sort_values(["reverse_step_index", "group"])


def suffix(values: list[object], length: int) -> tuple[object, ...] | None:
    if len(values) < length:
        return None
    return tuple(values[-length:])


def terminal_vector(sub: pd.DataFrame, cols: list[str], length: int) -> np.ndarray:
    tail = sub.sort_values("step_index").tail(length)
    values = []
    for col in cols:
        vals = tail[col].astype(float).tolist()
        if len(vals) < length:
            vals = [np.nan] * (length - len(vals)) + vals
        values.extend(vals)
    return np.array(values, dtype=float)


def build_difference_candidates(stage: pd.DataFrame) -> pd.DataFrame:
    traj = []
    for (sample_id, trajectory_id), sub in stage.groupby(["sample_id", "trajectory_id"], sort=False):
        s = sub.sort_values("step_index").reset_index(drop=True)
        traj.append(
            {
                "sample_id": sample_id,
                "trajectory_id": trajectory_id,
                "contains_miss": bool(s["contains_miss"].max()),
                "contains_control": bool(s["contains_control"].max()),
                "bands": s["band"].tolist(),
                "k": s["transition_k"].astype(float).tolist(),
                "sub": s,
            }
        )
    miss = [t for t in traj if t["contains_miss"]]
    controls = [t for t in traj if t["contains_control"] and not t["contains_miss"]]
    rows = []
    for m in miss:
        best = None
        for c in controls:
            shared_len = 0
            for length in [4, 3, 2]:
                if suffix(m["bands"], length) == suffix(c["bands"], length):
                    shared_len = length
                    break
            if not shared_len:
                continue
            mk = np.array(m["k"][-shared_len:], dtype=float)
            ck = np.array(c["k"][-shared_len:], dtype=float)
            k_dist = float(np.nanmean(np.abs(mk - ck)))
            mr = terminal_vector(m["sub"], ["R_before"], shared_len)
            cr = terminal_vector(c["sub"], ["R_before"], shared_len)
            r_dist = float(np.nanmean(np.abs(mr - cr)))
            score = (-shared_len, k_dist, r_dist)
            if best is None or score < best[0]:
                best = (score, c, shared_len)
        if best is None:
            continue
        _, c, shared_len = best
        idx = -shared_len
        msub = m["sub"].reset_index(drop=True)
        csub = c["sub"].reset_index(drop=True)
        mi = len(msub) + idx
        ci = len(csub) + idx
        if mi < 0 or ci < 0:
            mi = len(msub) - 1
            ci = len(csub) - 1
            idx = 0
        mr = msub.iloc[mi]
        cr = csub.iloc[ci]
        rows.append(
            {
                "miss_sample_id": m["sample_id"],
                "miss_trajectory_id": m["trajectory_id"],
                "control_sample_id": c["sample_id"],
                "control_trajectory_id": c["trajectory_id"],
                "shared_suffix_length": int(shared_len),
                "first_divergence_reverse_index": int(idx),
                "miss_R_before": mr["R_before"],
                "control_R_before": cr["R_before"],
                "delta_R_before": mr["R_before"] - cr["R_before"],
                "miss_R_drop": mr["R_drop"],
                "control_R_drop": cr["R_drop"],
                "delta_R_drop": mr["R_drop"] - cr["R_drop"],
                "miss_k": mr["transition_k"],
                "control_k": cr["transition_k"],
                "delta_k": mr["transition_k"] - cr["transition_k"],
                "miss_exit_distance": mr["exit_distance"],
                "control_exit_distance": cr["exit_distance"],
                "delta_exit_distance": mr["exit_distance"] - cr["exit_distance"],
            }
        )
    return pd.DataFrame(rows)


def kmeans(features: np.ndarray, k: int, iterations: int = 60) -> np.ndarray:
    n = len(features)
    if n == 0:
        return np.array([], dtype=int)
    k = min(k, n)
    init_idx = np.linspace(0, n - 1, k, dtype=int)
    centers = features[init_idx].copy()
    labels = np.zeros(n, dtype=int)
    for _ in range(iterations):
        dists = ((features[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        new_labels = dists.argmin(axis=1)
        if np.array_equal(labels, new_labels):
            break
        labels = new_labels
        for j in range(k):
            if np.any(labels == j):
                centers[j] = features[labels == j].mean(axis=0)
    return labels


def build_cluster_table(stage: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    traj_rows = []
    feature_rows = []
    cols = ["transition_k", "R_drop", "exit_distance"]
    for (sample_id, trajectory_id), sub in stage.groupby(["sample_id", "trajectory_id"], sort=False):
        sub = sub.sort_values("step_index").reset_index(drop=True)
        vector = terminal_vector(sub, cols, MAX_CLUSTER_STEPS)
        traj_rows.append(
            {
                "sample_id": sample_id,
                "trajectory_id": trajectory_id,
                "contains_miss": bool(sub["contains_miss"].max()),
                "contains_control": bool(sub["contains_control"].max()),
                "R_before_sequence": seq(sub["R_before"].tolist()),
                "R_drop_sequence": seq(sub["R_drop"].tolist()),
                "transition_k_sequence": seq(sub["transition_k"].tolist()),
                "exit_distance_sequence": seq(sub["exit_distance"].tolist()),
            }
        )
        feature_rows.append(vector)
    traj_df = pd.DataFrame(traj_rows)
    features = np.vstack(feature_rows)
    col_means = np.nanmean(features, axis=0)
    features = np.where(np.isnan(features), col_means, features)
    scale = features.std(axis=0)
    scale[scale == 0] = 1.0
    z = (features - features.mean(axis=0)) / scale
    traj_df["cluster_id"] = kmeans(z, N_CLUSTERS) + 1

    rows = []
    for cluster_id, sub in traj_df.groupby("cluster_id"):
        miss_count = int(sub["contains_miss"].sum())
        control_count = int(sub["contains_control"].sum())
        denom = miss_count + control_count
        rep = sub.iloc[0]
        rows.append(
            {
                "cluster_id": int(cluster_id),
                "trajectory_count": int(len(sub)),
                "miss_count": miss_count,
                "control_count": control_count,
                "miss_rate": float(miss_count / denom) if denom else 0.0,
                "representative_R_before_sequence": rep["R_before_sequence"],
                "representative_R_drop_sequence": rep["R_drop_sequence"],
                "representative_k_sequence": rep["transition_k_sequence"],
                "representative_exit_distance_sequence": rep["exit_distance_sequence"],
            }
        )
    return pd.DataFrame(rows).sort_values("trajectory_count", ascending=False), traj_df


def slope(values: pd.Series) -> float:
    y = to_float_series(values).dropna().to_numpy(dtype=float)
    if len(y) < 2:
        return 0.0
    x = np.arange(len(y), dtype=float)
    return float(np.polyfit(x, y, 1)[0])


def build_gradient_signature(stage: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (sample_id, trajectory_id), sub in stage.groupby(["sample_id", "trajectory_id"], sort=False):
        sub = sub.sort_values("step_index")
        rb = sub["R_before"].astype(float).to_numpy()
        rd = sub["R_drop"].astype(float).to_numpy()
        k = sub["transition_k"].astype(float).to_numpy()
        ed = sub["exit_distance"].astype(float).to_numpy()
        rb_diff = np.diff(rb)
        rd_diff = np.diff(rd)
        k_diff = np.diff(k)
        rows.append(
            {
                "sample_id": sample_id,
                "trajectory_id": trajectory_id,
                "contains_miss": bool(sub["contains_miss"].max()),
                "contains_control": bool(sub["contains_control"].max()),
                "monotonicity_R_before": float(np.mean(rb_diff <= 0)) if len(rb_diff) else 1.0,
                "total_variation_R_drop": float(np.sum(np.abs(rd_diff))) if len(rd_diff) else 0.0,
                "k_variation": float(np.sum(np.abs(k_diff))) if len(k_diff) else 0.0,
                "exit_distance_slope": slope(sub["exit_distance"]),
                "exit_distance_total_change": float(ed[-1] - ed[0]) if len(ed) else 0.0,
                "max_local_jump_R_drop": float(np.max(np.abs(rd_diff))) if len(rd_diff) else 0.0,
                "max_local_jump_k": float(np.max(np.abs(k_diff))) if len(k_diff) else 0.0,
                "residence_like_length": int(np.sum(ed > 0)),
            }
        )
    return pd.DataFrame(rows)


def draw_axes(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], title: str, y_label: str, x_vals: list[int], y_min: float, y_max: float) -> None:
    l, t, r, b = box
    draw.rectangle(box, outline="#2f3b44", width=2)
    draw.text((l, t - 55), title, fill="#1f2a33", font=font(30, True))
    draw.text((l, b + 35), "reverse_step_index (terminal = 0)", fill="#1f2a33", font=font(16))
    draw.text((l - 70, t - 30), y_label, fill="#1f2a33", font=font(16))
    small = font(13)
    for frac in np.linspace(0, 1, 5):
        y = b - frac * (b - t)
        val = y_min + frac * (y_max - y_min)
        draw.line((l, y, r, y), fill="#e0e6eb", width=1)
        draw.text((l - 58, y - 8), f"{val:.1f}", fill="#3a4650", font=small)
    for x in x_vals:
        if len(x_vals) <= 1:
            xp = l
        else:
            xp = l + (x - min(x_vals)) / (max(x_vals) - min(x_vals)) * (r - l)
        draw.line((xp, b, xp, b + 5), fill="#2f3b44", width=1)
        if x % 2 == 0 or x == 0:
            draw.text((xp - 9, b + 10), str(x), fill="#3a4650", font=small)


def plot_overlay(aligned: pd.DataFrame, quantity: str, title: str, path: Path) -> None:
    width, height = 1700, 1000
    box = (130, 110, width - 80, height - 120)
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    x_vals = sorted(aligned["reverse_step_index"].unique().tolist())
    y = to_float_series(aligned[quantity]).dropna()
    y_min, y_max = float(y.quantile(0.01)), float(y.quantile(0.99))
    if y_min == y_max:
        y_min -= 1
        y_max += 1
    draw_axes(draw, box, title, quantity, x_vals, y_min, y_max)

    l, t, r, b = box

    def map_point(x: int, val: float) -> tuple[float, float]:
        xp = l + (x - min(x_vals)) / max(1, (max(x_vals) - min(x_vals))) * (r - l)
        yp = b - (val - y_min) / (y_max - y_min) * (b - t)
        return xp, max(t, min(b, yp))

    colors = {"other": "#c8cdd2", "control": "#7ba7d3", "miss": "#d7837f"}
    strong = {"other": "#6e747a", "control": "#1f6fab", "miss": "#b9413b"}
    work = aligned.copy()
    work["group"] = work.apply(group_name, axis=1)
    for (_, _), sub in work.groupby(["sample_id", "trajectory_id"], sort=False):
        grp = sub["group"].iloc[0]
        pts = [(int(row.reverse_step_index), float(getattr(row, quantity))) for row in sub.itertuples(index=False) if pd.notna(getattr(row, quantity))]
        if len(pts) >= 2:
            mapped = [map_point(x, v) for x, v in pts]
            draw.line(mapped, fill=colors[grp], width=1)
    for grp, sub in work.groupby("group"):
        med = sub.groupby("reverse_step_index")[quantity].median().dropna()
        pts = [(int(x), float(v)) for x, v in med.items()]
        if len(pts) >= 2:
            draw.line([map_point(x, v) for x, v in pts], fill=strong[grp], width=5)
    legend_x = r - 330
    legend_y = t + 18
    for i, grp in enumerate(["miss", "control", "other"]):
        y0 = legend_y + i * 28
        draw.line((legend_x, y0 + 8, legend_x + 45, y0 + 8), fill=strong[grp], width=5)
        draw.text((legend_x + 55, y0), grp, fill=strong[grp], font=font(15, True))
    img.save(path)


def plot_heatmap(summary: pd.DataFrame, path: Path) -> None:
    pivot = summary.pivot(index="reverse_step_index", columns="group")
    rows = []
    for rev in sorted(summary["reverse_step_index"].unique()):
        row = {"reverse_step_index": rev}
        for quantity, col in [
            ("median_R_before difference", "median_R_before"),
            ("median_R_drop difference", "median_R_drop"),
            ("median_k difference", "median_k"),
            ("median_exit_distance difference", "median_exit_distance"),
        ]:
            miss = summary[(summary["reverse_step_index"] == rev) & (summary["group"] == "miss")][col]
            control = summary[(summary["reverse_step_index"] == rev) & (summary["group"] == "control")][col]
            row[quantity] = float(miss.iloc[0] - control.iloc[0]) if len(miss) and len(control) else np.nan
        rows.append(row)
    data = pd.DataFrame(rows)
    quantities = [c for c in data.columns if c != "reverse_step_index"]
    cell_w, cell_h = 210, 42
    left, top = 190, 120
    width = left + cell_w * len(quantities) + 90
    height = top + cell_h * len(data) + 100
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    draw.text((50, 35), "Miss-control median numeric differences", fill="#1f2a33", font=font(28, True))
    vals = data[quantities].to_numpy(dtype=float)
    max_abs = np.nanmax(np.abs(vals)) if np.isfinite(vals).any() else 1.0
    max_abs = max(max_abs, 1.0)
    for j, qname in enumerate(quantities):
        draw.text((left + j * cell_w + 8, top - 48), qname.replace(" difference", ""), fill="#1f2a33", font=font(13, True))
    for i, rrow in data.iterrows():
        y = top + i * cell_h
        draw.text((55, y + 12), str(int(rrow["reverse_step_index"])), fill="#1f2a33", font=font(13))
        for j, qname in enumerate(quantities):
            val = rrow[qname]
            x = left + j * cell_w
            if pd.isna(val):
                color = "#f0f0f0"
                txt = "NA"
            else:
                color = blend_hex("#f5f7fb", "#b9413b", max(0, val) / max_abs) if val >= 0 else blend_hex("#f5f7fb", "#1f6fab", abs(val) / max_abs)
                txt = f"{val:.1f}"
            draw.rectangle((x, y, x + cell_w - 2, y + cell_h - 2), fill=color, outline="#d7dde2")
            draw.text((x + 70, y + 12), txt, fill="#17232c", font=font(13))
    img.save(path)


def plot_divergence(candidates: pd.DataFrame, path: Path) -> None:
    counts = candidates["first_divergence_reverse_index"].value_counts().sort_index()
    width, height = 1100, 760
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    draw.text((60, 35), "Paired route first-divergence reverse index", fill="#1f2a33", font=font(28, True))
    l, t, r, b = 120, 120, width - 80, height - 100
    draw.rectangle((l, t, r, b), outline="#2f3b44", width=2)
    max_c = max(int(counts.max()) if len(counts) else 0, 1)
    xs = counts.index.tolist()
    for i, xval in enumerate(xs):
        x0 = l + i * ((r - l) / max(1, len(xs)))
        x1 = l + (i + 0.75) * ((r - l) / max(1, len(xs)))
        h = (b - t) * counts.loc[xval] / max_c
        draw.rectangle((x0, b - h, x1, b), fill="#9b6fb3")
        draw.text((x0 + 4, b + 10), str(int(xval)), fill="#1f2a33", font=font(13))
        draw.text((x0 + 4, b - h - 22), str(int(counts.loc[xval])), fill="#1f2a33", font=font(13))
    draw.text((l, b + 45), "reverse_step_index", fill="#1f2a33", font=font(15))
    img.save(path)


def write_report(
    table: pd.DataFrame,
    aligned: pd.DataFrame,
    summary: pd.DataFrame,
    candidates: pd.DataFrame,
    clusters: pd.DataFrame,
    gradient: pd.DataFrame,
) -> None:
    lines = []
    lines.append("# Numeric Trajectory Anatomy Report")
    lines.append("")
    lines.append("finite-sample observational note: this report treats numeric traces as finite observed trajectories in the available CSV rows.")
    lines.append("")
    lines.append("## 1. Motivation")
    lines.append("")
    lines.append("The route grammar based on state labels was tidy, but it mostly showed the labels back to us. This pass reduces the role of semantic labels and asks what the numeric path itself looks like.")
    lines.append("")
    lines.append("## 2. Why labels were reduced")
    lines.append("")
    lines.append("The main path variables here are `R_before`, `R_after`, `R_drop`, `transition_k`, `exit_distance`, and `remaining_K_before`. The source columns are `last_before_R`, `last_after_R`, `boundary_k_num`, and `last_before_exit_distance` in `band_stage_boundary_detail.csv`; `remaining_K_before` is kept as the same local R coordinate for compatibility with the event tables. Band and miss/control are used only as auxiliary identifiers.")
    lines.append("")
    lines.append("## 3. Numeric trajectory construction")
    lines.append("")
    lines.append(f"The stage rows were ordered by `sample_id + trajectory_id + first_entry_index`. This produced {len(table):,} trajectory traces from {len(aligned):,} numeric stage rows. Each trajectory stores the full numeric sequences and compact summary features such as total drop, mean drop, max k, and exit-distance range.")
    lines.append("")
    lines.append("## 4. Terminal-aligned paths")
    lines.append("")
    lines.append("The terminal-aligned table sets the last observed stage to reverse index `0`, then indexes upstream stages as `-1`, `-2`, and so on. This makes capture-side convergence visible without using caught/avoid/front labels as the organizing axis.")
    lines.append("")
    lines.append("## 5. Miss/control numeric comparison")
    lines.append("")
    lines.append("Median summaries by reverse index show whether miss and control traces separate near the terminal side or earlier upstream. A compact view of the first aligned indices is:")
    lines.append("")
    lines.append("| reverse_step_index | group | count | median_R_before | median_R_drop | median_k | median_exit_distance |")
    lines.append("|---:|---|---:|---:|---:|---:|---:|")
    for r in summary[summary["reverse_step_index"].isin([-5, -4, -3, -2, -1, 0])].head(18).itertuples(index=False):
        lines.append(f"| {int(r.reverse_step_index)} | {r.group} | {int(r.count)} | {finite(r.median_R_before):.1f} | {finite(r.median_R_drop):.1f} | {finite(r.median_k):.1f} | {finite(r.median_exit_distance):.1f} |")
    lines.append("")
    lines.append("## 6. Paired route differences")
    lines.append("")
    lines.append("Miss trajectories were paired to control trajectories that shared a terminal band suffix of length 2-4, with transition-k suffix closeness used as a secondary preference. The table then records the first upstream index just outside the shared suffix window.")
    lines.append("")
    lines.append("| shared_suffix_length | first_divergence_reverse_index | pair_count | median_delta_R_before | median_delta_R_drop | median_delta_k | median_delta_exit_distance |")
    lines.append("|---:|---:|---:|---:|---:|---:|---:|")
    if len(candidates):
        agg = candidates.groupby(["shared_suffix_length", "first_divergence_reverse_index"]).agg(
            pair_count=("delta_R_before", "size"),
            median_delta_R_before=("delta_R_before", "median"),
            median_delta_R_drop=("delta_R_drop", "median"),
            median_delta_k=("delta_k", "median"),
            median_delta_exit_distance=("delta_exit_distance", "median"),
        ).reset_index().sort_values("pair_count", ascending=False)
        for r in agg.head(10).itertuples(index=False):
            lines.append(f"| {int(r.shared_suffix_length)} | {int(r.first_divergence_reverse_index)} | {int(r.pair_count)} | {float(r.median_delta_R_before):.1f} | {float(r.median_delta_R_drop):.1f} | {float(r.median_delta_k):.1f} | {float(r.median_delta_exit_distance):.1f} |")
    lines.append("")
    lines.append("## 7. Numeric path clusters")
    lines.append("")
    lines.append("A simple terminal-window clustering used the last six steps of `transition_k`, `R_drop`, and `exit_distance`, with missing upstream positions filled by column means after alignment. This is a shape grouping, not a semantic route family.")
    lines.append("")
    lines.append("| cluster_id | trajectory_count | miss_count | control_count | miss_rate |")
    lines.append("|---:|---:|---:|---:|---:|")
    for r in clusters.itertuples(index=False):
        lines.append(f"| {int(r.cluster_id)} | {int(r.trajectory_count):,} | {int(r.miss_count)} | {int(r.control_count)} | {float(r.miss_rate):.3f} |")
    lines.append("")
    lines.append("## 8. Gradient signatures")
    lines.append("")
    lines.append("The gradient signature table records simple shape features: R monotonicity, variation in drops, variation in k, exit-distance slope, total exit-distance change, local jumps, and a residence-like length counted from positive exit-distance stages.")
    lines.append("")
    g = gradient.groupby(["contains_miss", "contains_control"]).agg(
        count=("trajectory_id", "size"),
        median_exit_distance_slope=("exit_distance_slope", "median"),
        median_k_variation=("k_variation", "median"),
        median_total_variation_R_drop=("total_variation_R_drop", "median"),
        median_residence_like_length=("residence_like_length", "median"),
    ).reset_index()
    lines.append("| contains_miss | contains_control | count | median_exit_distance_slope | median_k_variation | median_total_variation_R_drop | median_residence_like_length |")
    lines.append("|---|---|---:|---:|---:|---:|---:|")
    for r in g.itertuples(index=False):
        lines.append(f"| {bool(r.contains_miss)} | {bool(r.contains_control)} | {int(r.count)} | {float(r.median_exit_distance_slope):.3f} | {float(r.median_k_variation):.1f} | {float(r.median_total_variation_R_drop):.1f} | {float(r.median_residence_like_length):.1f} |")
    lines.append("")
    lines.append("## 9. Interpretation")
    lines.append("")
    lines.append("The numeric view shifts attention from named route families to path shape. The terminal alignment makes it easy to ask whether miss/control share the same broad road and where their local numeric traces begin to separate. `exit_distance` can now be read as a graded coordinate along the path rather than as a front label, while `transition_k` appears as part of a short terminal shape instead of only as a family name. In this view, `32-63` is less a standalone object and more a region where the remaining-K trace is large enough for several nearby numeric shapes to be visible.")
    lines.append("")
    lines.append("## 10. Limits")
    lines.append("")
    lines.append("The broad trajectory table uses stage-level boundary rows, while miss/control labels come from the event-detail CSV. The pairing and clustering are intentionally simple first-pass devices for finding candidate numeric differences; they are not mechanisms.")
    lines.append("")
    lines.append("finite-sample observational note: these outputs describe numeric path shapes in this dataset only; they do not assert proof, mechanism, generalization, counterexample, or any claim about the Collatz conjecture.")
    lines.append("")
    lines.append("## Output files")
    lines.append("")
    for name in [
        "numeric_trajectory_table.csv",
        "aligned_numeric_paths.csv",
        "miss_control_numeric_path_summary.csv",
        "route_difference_candidates.csv",
        "numeric_path_cluster_table.csv",
        "gradient_signature_table.csv",
        "R_before_paths_overlay.png",
        "R_drop_paths_overlay.png",
        "k_paths_overlay.png",
        "exit_distance_paths_overlay.png",
        "miss_control_numeric_summary_heatmap.png",
        "paired_route_difference_plot.png",
    ]:
        lines.append(f"- `{name}`")
    lines.append("")
    lines.append("## Source files")
    lines.append("")
    lines.append(f"- `{STAGE_CSV}`")
    lines.append(f"- `{EVENT_CSV}`")
    (OUT / "numeric_trajectory_anatomy_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    stage = add_labels(prepare_stage_rows())
    table = build_numeric_trajectory_table(stage)
    aligned = build_aligned_paths(stage)
    summary = build_numeric_summary(aligned)
    candidates = build_difference_candidates(stage)
    clusters, cluster_assignment = build_cluster_table(stage)
    gradient = build_gradient_signature(stage)

    table.to_csv(OUT / "numeric_trajectory_table.csv", index=False, encoding="utf-8")
    aligned.to_csv(OUT / "aligned_numeric_paths.csv", index=False, encoding="utf-8")
    summary.to_csv(OUT / "miss_control_numeric_path_summary.csv", index=False, encoding="utf-8")
    candidates.to_csv(OUT / "route_difference_candidates.csv", index=False, encoding="utf-8")
    clusters.to_csv(OUT / "numeric_path_cluster_table.csv", index=False, encoding="utf-8")
    gradient.to_csv(OUT / "gradient_signature_table.csv", index=False, encoding="utf-8")
    cluster_assignment.to_csv(OUT / "numeric_path_cluster_assignments.csv", index=False, encoding="utf-8")

    plot_overlay(aligned, "R_before", "Terminal-aligned R_before paths", OUT / "R_before_paths_overlay.png")
    plot_overlay(aligned, "R_drop", "Terminal-aligned R_drop paths", OUT / "R_drop_paths_overlay.png")
    plot_overlay(aligned, "transition_k", "Terminal-aligned transition_k paths", OUT / "k_paths_overlay.png")
    plot_overlay(aligned, "exit_distance", "Terminal-aligned exit_distance paths", OUT / "exit_distance_paths_overlay.png")
    plot_heatmap(summary, OUT / "miss_control_numeric_summary_heatmap.png")
    plot_divergence(candidates, OUT / "paired_route_difference_plot.png")
    write_report(table, aligned, summary, candidates, clusters, gradient)

    meta = {
        "stage_rows": int(len(stage)),
        "trajectories": int(len(table)),
        "miss_bearing_trajectories": int(table["contains_miss"].sum()),
        "control_bearing_trajectories": int(table["contains_control"].sum()),
        "paired_difference_rows": int(len(candidates)),
        "cluster_rows": int(len(clusters)),
        "output_dir": str(OUT),
        "source_stage_csv": str(STAGE_CSV),
        "source_event_csv": str(EVENT_CSV),
    }
    (OUT / "run_summary.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
