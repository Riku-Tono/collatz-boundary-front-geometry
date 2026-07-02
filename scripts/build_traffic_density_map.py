from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageColor, ImageDraw, ImageFont


ROOT = Path(r"C:\Users\yauki\Documents\Codex\2026-07-01\csv-collatz-state-band-boundary-front")
IN = ROOT / "outputs" / "numeric_trajectory_anatomy"
OUT = ROOT / "outputs" / "traffic_density_map"

BAND_ORDER = ["4-7", "8-15", "16-31", "32-63", "64-127", "128-255", "256-511"]


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


def blend_hex(c1: str, c2: str, t: float) -> tuple[int, int, int]:
    a = np.array(ImageColor.getrgb(c1), dtype=float)
    b = np.array(ImageColor.getrgb(c2), dtype=float)
    return tuple(np.round(a * (1 - t) + b * t).astype(int))


def group_name(row: pd.Series) -> str:
    if bool(row["contains_miss"]):
        return "miss"
    if bool(row["contains_control"]):
        return "control"
    return "other"


def band_key(band: str) -> tuple[int, str]:
    if band in BAND_ORDER:
        return (BAND_ORDER.index(band), band)
    return (len(BAND_ORDER), band)


def add_group(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["group"] = out.apply(group_name, axis=1)
    return out


def density_table(df: pd.DataFrame, dims: list[str], name: str) -> pd.DataFrame:
    g = df.groupby(dims, dropna=False)
    rows = []
    total = len(df)
    for key, sub in g:
        if not isinstance(key, tuple):
            key = (key,)
        row = {dim: val for dim, val in zip(dims, key)}
        miss_count = int(sub["contains_miss"].sum())
        control_count = int(sub["contains_control"].sum())
        count = int(len(sub))
        row.update(
            {
                "coordinate_system": name,
                "count": count,
                "probability": count / total if total else 0.0,
                "trajectory_count": int(sub[["sample_id", "trajectory_id"]].drop_duplicates().shape[0]),
                "miss_count": miss_count,
                "control_count": control_count,
                "other_count": int(count - miss_count - control_count),
                "miss_share": miss_count / count if count else 0.0,
                "control_share": control_count / count if count else 0.0,
                "median_R_drop": float(sub["R_drop"].median()),
                "mean_R_drop": float(sub["R_drop"].mean()),
                "median_k": float(sub["transition_k"].median()),
                "mean_k": float(sub["transition_k"].mean()),
                "median_exit_distance": float(sub["exit_distance"].median()),
                "mean_exit_distance": float(sub["exit_distance"].mean()),
            }
        )
        rows.append(row)
    return pd.DataFrame(rows).sort_values("count", ascending=False)


def flow_speed_table(df: pd.DataFrame) -> pd.DataFrame:
    tables = []
    specs = [
        (["R_before"], "R_before"),
        (["exit_distance"], "exit_distance"),
        (["band"], "band"),
        (["band", "R_before"], "band_R_before"),
        (["R_before", "transition_k"], "R_before_k"),
        (["R_before", "exit_distance"], "R_before_exit_distance"),
    ]
    for dims, name in specs:
        t = density_table(df, dims, name)
        keep = dims + [
            "coordinate_system",
            "count",
            "trajectory_count",
            "median_R_drop",
            "mean_R_drop",
            "median_k",
            "mean_k",
            "median_exit_distance",
            "miss_count",
            "miss_share",
        ]
        tables.append(t[keep])
    return pd.concat(tables, ignore_index=True)


def occupancy_summary(df: pd.DataFrame) -> pd.DataFrame:
    by_band = density_table(df, ["band"], "band")
    by_r = density_table(df, ["R_before"], "R_before")
    by_exit = density_table(df, ["exit_distance"], "exit_distance")
    rows = []
    for name, t, coord in [
        ("band", by_band, "band"),
        ("R_before", by_r, "R_before"),
        ("exit_distance", by_exit, "exit_distance"),
    ]:
        top = t.iloc[0]
        rows.append(
            {
                "axis": name,
                "top_coordinate": top[coord],
                "top_count": int(top["count"]),
                "top_probability": float(top["probability"]),
                "top_miss_share": float(top["miss_share"]),
                "unique_coordinates": int(len(t)),
            }
        )
    return pd.DataFrame(rows)


def matrix_from_table(table: pd.DataFrame, x_col: str, y_col: str, value_col: str = "count") -> tuple[list, list, np.ndarray]:
    xs = sorted(table[x_col].dropna().unique().tolist())
    ys = sorted(table[y_col].dropna().unique().tolist())
    if x_col == "band":
        xs = sorted(xs, key=band_key)
    if y_col == "band":
        ys = sorted(ys, key=band_key)
    mat = np.zeros((len(ys), len(xs)), dtype=float)
    lookup = table.set_index([y_col, x_col])[value_col].to_dict()
    for i, y in enumerate(ys):
        for j, x in enumerate(xs):
            mat[i, j] = lookup.get((y, x), 0.0)
    return xs, ys, mat


def draw_heatmap(
    table: pd.DataFrame,
    x_col: str,
    y_col: str,
    value_col: str,
    title: str,
    path: Path,
    log_scale: bool = True,
    max_dim: int = 900,
) -> None:
    xs, ys, mat = matrix_from_table(table, x_col, y_col, value_col)
    display = np.log1p(mat) if log_scale else mat.copy()
    max_val = max(float(np.nanmax(display)), 1.0)
    cell = max(16, min(58, int(max_dim / max(len(xs), len(ys), 1))))
    left, top = 145, 120
    width = left + cell * len(xs) + 90
    height = top + cell * len(ys) + 95
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    draw.text((50, 35), title, fill="#1e2a33", font=font(28, True))
    draw.text((50, 72), f"value={value_col}; {'log color scale' if log_scale else 'linear color scale'}", fill="#4a5963", font=font(14))
    small = font(11)
    for j, x in enumerate(xs):
        if j % max(1, math.ceil(len(xs) / 18)) == 0:
            draw.text((left + j * cell, top - 24), str(x), fill="#25313a", font=small)
    for i, y in enumerate(ys):
        draw.text((45, top + i * cell + cell / 2 - 7), str(y), fill="#25313a", font=small)
    for i, y in enumerate(ys):
        for j, x in enumerate(xs):
            v = display[i, j]
            color = blend_hex("#f8fbff", "#0d5b8c", v / max_val if max_val else 0.0)
            x0 = left + j * cell
            y0 = top + i * cell
            draw.rectangle((x0, y0, x0 + cell - 1, y0 + cell - 1), fill=color, outline="#e5ebef")
            raw = mat[i, j]
            if raw and cell >= 34:
                fill = "white" if v / max_val > 0.55 else "#17232c"
                draw.text((x0 + 4, y0 + cell / 2 - 7), str(int(raw)), fill=fill, font=small)
    draw.text((left + cell * len(xs) / 2 - 30, height - 42), x_col, fill="#1e2a33", font=font(14))
    draw.text((32, top - 44), y_col, fill="#1e2a33", font=font(14))
    img.save(path)


def draw_miss_overlay_heatmap(table: pd.DataFrame, x_col: str, y_col: str, title: str, path: Path) -> None:
    xs, ys, mat = matrix_from_table(table, x_col, y_col, "count")
    _, _, miss = matrix_from_table(table, x_col, y_col, "miss_count")
    display = np.log1p(mat)
    max_val = max(float(np.nanmax(display)), 1.0)
    cell = max(20, min(62, int(900 / max(len(xs), len(ys), 1))))
    left, top = 145, 120
    width = left + cell * len(xs) + 90
    height = top + cell * len(ys) + 95
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    draw.text((50, 35), title, fill="#1e2a33", font=font(28, True))
    draw.text((50, 72), "blue=count density; red dot area=miss rows", fill="#4a5963", font=font(14))
    small = font(11)
    for j, x in enumerate(xs):
        if j % max(1, math.ceil(len(xs) / 18)) == 0:
            draw.text((left + j * cell, top - 24), str(x), fill="#25313a", font=small)
    for i, y in enumerate(ys):
        draw.text((45, top + i * cell + cell / 2 - 7), str(y), fill="#25313a", font=small)
    max_miss = max(float(np.nanmax(miss)), 1.0)
    for i in range(len(ys)):
        for j in range(len(xs)):
            v = display[i, j]
            x0 = left + j * cell
            y0 = top + i * cell
            draw.rectangle((x0, y0, x0 + cell - 1, y0 + cell - 1), fill=blend_hex("#f8fbff", "#0d5b8c", v / max_val), outline="#e5ebef")
            if miss[i, j] > 0:
                radius = max(3, (cell / 2 - 4) * math.sqrt(miss[i, j] / max_miss))
                cx = x0 + cell / 2
                cy = y0 + cell / 2
                draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill="#bd3f3b")
    draw.text((left + cell * len(xs) / 2 - 30, height - 42), x_col, fill="#1e2a33", font=font(14))
    draw.text((32, top - 44), y_col, fill="#1e2a33", font=font(14))
    img.save(path)


def draw_top_bar(table: pd.DataFrame, label_col: str, title: str, path: Path, top_n: int = 25) -> None:
    data = table.sort_values("count", ascending=False).head(top_n).iloc[::-1]
    width, row_h = 1300, 34
    left, top, right = 360, 92, 80
    height = top + row_h * len(data) + 80
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    draw.text((50, 30), title, fill="#1e2a33", font=font(28, True))
    max_count = max(float(data["count"].max()), 1.0)
    axis_w = width - left - right
    for i, row in enumerate(data.itertuples(index=False)):
        y = top + i * row_h
        label = str(getattr(row, label_col))
        draw.text((55, y + 7), label, fill="#1e2a33", font=font(13))
        w = axis_w * float(row.count) / max_count
        draw.rounded_rectangle((left, y + 6, left + w, y + row_h - 6), radius=5, fill="#5d89b3")
        draw.text((left + w + 8, y + 7), f"{int(row.count)}", fill="#1e2a33", font=font(12))
    img.save(path)


def write_report(
    aligned: pd.DataFrame,
    traffic: pd.DataFrame,
    flow: pd.DataFrame,
    occupancy: pd.DataFrame,
    top_coords: pd.DataFrame,
) -> None:
    lines = []
    lines.append("# Traffic Density Map Report")
    lines.append("")
    lines.append("finite-sample observational note: this report treats the numeric stage rows as a finite traffic map over the observed coordinate space.")
    lines.append("")
    lines.append("## Motivation")
    lines.append("")
    lines.append("The previous miss/control comparisons showed local differences but did not make miss a separate world. This report changes the subject: the main object is the traffic geometry of all trajectories, with miss/control used only as light overlays.")
    lines.append("")
    lines.append("## Input")
    lines.append("")
    lines.append(f"The map uses {len(aligned):,} aligned numeric stage rows from {aligned[['sample_id','trajectory_id']].drop_duplicates().shape[0]:,} trajectories. Coordinates are `band`, `R_before`, `transition_k`, and `exit_distance`; speed is summarized by `R_drop` / `transition_k`.")
    lines.append("")
    lines.append("## Occupancy")
    lines.append("")
    lines.append("| axis | top_coordinate | top_count | top_probability | top_miss_share | unique_coordinates |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for r in occupancy.itertuples(index=False):
        lines.append(f"| {r.axis} | {r.top_coordinate} | {int(r.top_count):,} | {float(r.top_probability):.3f} | {float(r.top_miss_share):.3f} | {int(r.unique_coordinates)} |")
    lines.append("")
    lines.append("## Densest Coordinates")
    lines.append("")
    lines.append("| coordinate_system | coordinate | count | median_R_drop | miss_share |")
    lines.append("|---|---|---:|---:|---:|")
    for r in top_coords.head(20).itertuples(index=False):
        coord_parts = []
        for col in ["band", "R_before", "transition_k", "exit_distance"]:
            if col in top_coords.columns:
                value = getattr(r, col)
                if pd.notna(value):
                    coord_parts.append(f"{col}={value}")
        coord = ", ".join(coord_parts)
        lines.append(f"| {r.coordinate_system} | {coord} | {int(r.count):,} | {float(r.median_R_drop):.1f} | {float(r.miss_share):.3f} |")
    lines.append("")
    lines.append("## Reading")
    lines.append("")
    lines.append("The density view puts the familiar staircase back into a traffic map. The busiest coordinates are not necessarily the most miss-rich coordinates; miss appears as a colored overlay on a broader road system. This supports the current turn in the analysis: first understand where traffic accumulates and how fast it moves, then ask where miss rows sit inside that terrain.")
    lines.append("")
    lines.append("## Limits")
    lines.append("")
    lines.append("The map uses stage-level boundary rows, so `R_drop` and `transition_k` are definitionally linked in this table. `exit_distance` is a translated position within a band. The figures are density maps of the current finite dataset, not a mechanism.")
    lines.append("")
    lines.append("finite-sample observational note: these outputs describe observed traffic geometry only; they do not assert proof, mechanism, generalization, counterexample, or any claim about the Collatz conjecture.")
    lines.append("")
    lines.append("## Output files")
    lines.append("")
    for name in [
        "traffic_density_table.csv",
        "flow_speed_table.csv",
        "coordinate_occupancy_summary.csv",
        "top_traffic_coordinates.csv",
        "R_before_vs_k_density.png",
        "R_before_vs_exit_distance_density.png",
        "band_R_before_density.png",
        "exit_distance_k_density.png",
        "traffic_density_with_miss_overlay.png",
        "top_R_before_traffic_bar.png",
        "traffic_density_map_report.md",
    ]:
        lines.append(f"- `{name}`")
    (OUT / "traffic_density_map_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    aligned = add_group(pd.read_csv(IN / "aligned_numeric_paths.csv"))

    density_specs = [
        (["R_before", "transition_k"], "R_before_k"),
        (["R_before", "exit_distance"], "R_before_exit_distance"),
        (["band", "R_before"], "band_R_before"),
        (["exit_distance", "transition_k"], "exit_distance_k"),
        (["band", "exit_distance"], "band_exit_distance"),
        (["R_before"], "R_before"),
        (["exit_distance"], "exit_distance"),
        (["band"], "band"),
    ]
    density_tables = [density_table(aligned, dims, name) for dims, name in density_specs]
    traffic = pd.concat(density_tables, ignore_index=True, sort=False)
    flow = flow_speed_table(aligned)
    occupancy = occupancy_summary(aligned)
    top_coords = traffic.sort_values("count", ascending=False)

    traffic.to_csv(OUT / "traffic_density_table.csv", index=False, encoding="utf-8")
    flow.to_csv(OUT / "flow_speed_table.csv", index=False, encoding="utf-8")
    occupancy.to_csv(OUT / "coordinate_occupancy_summary.csv", index=False, encoding="utf-8")
    top_coords.head(200).to_csv(OUT / "top_traffic_coordinates.csv", index=False, encoding="utf-8")

    rk = traffic[traffic["coordinate_system"].eq("R_before_k")].copy()
    re = traffic[traffic["coordinate_system"].eq("R_before_exit_distance")].copy()
    br = traffic[traffic["coordinate_system"].eq("band_R_before")].copy()
    ek = traffic[traffic["coordinate_system"].eq("exit_distance_k")].copy()

    draw_heatmap(rk, "R_before", "transition_k", "count", "R_before vs k traffic density", OUT / "R_before_vs_k_density.png")
    draw_heatmap(re, "R_before", "exit_distance", "count", "R_before vs exit_distance traffic density", OUT / "R_before_vs_exit_distance_density.png")
    draw_heatmap(br, "R_before", "band", "count", "Band vs R_before traffic density", OUT / "band_R_before_density.png")
    draw_heatmap(ek, "exit_distance", "transition_k", "count", "Exit_distance vs k traffic density", OUT / "exit_distance_k_density.png")
    draw_miss_overlay_heatmap(rk, "R_before", "transition_k", "Traffic density with miss overlay", OUT / "traffic_density_with_miss_overlay.png")
    draw_top_bar(traffic[traffic["coordinate_system"].eq("R_before")], "R_before", "Top R_before traffic coordinates", OUT / "top_R_before_traffic_bar.png")

    write_report(aligned, traffic, flow, occupancy, top_coords)
    meta = {
        "stage_rows": int(len(aligned)),
        "trajectories": int(aligned[["sample_id", "trajectory_id"]].drop_duplicates().shape[0]),
        "traffic_rows": int(len(traffic)),
        "flow_rows": int(len(flow)),
        "output_dir": str(OUT),
    }
    (OUT / "run_summary.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
