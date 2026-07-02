from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageColor, ImageDraw, ImageFont


ROOT = Path(r"C:\Users\yauki\Documents\Codex\2026-07-01\csv-collatz-state-band-boundary-front")
IN = ROOT / "outputs" / "numeric_trajectory_anatomy"
PAIR_IN = ROOT / "outputs" / "paired_numeric_difference_map"
OUT = ROOT / "outputs" / "alignment_coordinate_comparison"

GROUPS = ["miss", "control", "other"]
COLORS = {"positive": "#bd3f3b", "negative": "#256fa8", "neutral": "#f6f7fb"}


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


def median_or_nan(series: pd.Series) -> float:
    vals = pd.to_numeric(series, errors="coerce").dropna()
    return float(vals.median()) if len(vals) else np.nan


def q_or_nan(series: pd.Series, q: float) -> float:
    vals = pd.to_numeric(series, errors="coerce").dropna()
    return float(vals.quantile(q)) if len(vals) else np.nan


def add_start_index(aligned: pd.DataFrame) -> pd.DataFrame:
    out = aligned.sort_values(["sample_id", "trajectory_id", "reverse_step_index"]).copy()
    out["start_step_index"] = out.groupby(["sample_id", "trajectory_id"]).cumcount()
    out["group"] = out.apply(group_name, axis=1)
    return out


def summarize_by_axis(df: pd.DataFrame, axis_col: str, quantities: list[str]) -> pd.DataFrame:
    rows = []
    for (coord, group), sub in df.groupby([axis_col, "group"], sort=True):
        row = {"alignment": axis_col, "coordinate": coord, "group": group, "count": int(len(sub))}
        for quantity in quantities:
            row[f"median_{quantity}"] = median_or_nan(sub[quantity])
            row[f"q25_{quantity}"] = q_or_nan(sub[quantity], 0.25)
            row[f"q75_{quantity}"] = q_or_nan(sub[quantity], 0.75)
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["coordinate", "group"])


def diff_from_summary(summary: pd.DataFrame, quantities: list[str]) -> pd.DataFrame:
    rows = []
    for coord, sub in summary.groupby("coordinate", sort=True):
        miss = sub[sub["group"].eq("miss")]
        control = sub[sub["group"].eq("control")]
        other = sub[sub["group"].eq("other")]
        row = {
            "alignment": sub["alignment"].iloc[0],
            "coordinate": coord,
            "miss_count": int(miss["count"].iloc[0]) if len(miss) else 0,
            "control_count": int(control["count"].iloc[0]) if len(control) else 0,
            "other_count": int(other["count"].iloc[0]) if len(other) else 0,
        }
        for quantity in quantities:
            m = miss[f"median_{quantity}"].iloc[0] if len(miss) else np.nan
            c = control[f"median_{quantity}"].iloc[0] if len(control) else np.nan
            o = other[f"median_{quantity}"].iloc[0] if len(other) else np.nan
            row[f"miss_minus_control_{quantity}"] = m - c if pd.notna(m) and pd.notna(c) else np.nan
            row[f"miss_minus_other_{quantity}"] = m - o if pd.notna(m) and pd.notna(o) else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def compact_signal(diff: pd.DataFrame, quantities: list[str], min_count: int = 10) -> dict[str, object]:
    eligible = diff[(diff["miss_count"] >= min_count) & (diff["control_count"] >= min_count)].copy()
    result: dict[str, object] = {
        "alignment": diff["alignment"].iloc[0] if len(diff) else "",
        "eligible_coordinate_count": int(len(eligible)),
    }
    best_score = -1.0
    best_coord = None
    best_quantity = None
    for quantity in quantities:
        col = f"miss_minus_control_{quantity}"
        vals = eligible[col].abs().dropna()
        result[f"max_abs_miss_minus_control_{quantity}"] = float(vals.max()) if len(vals) else np.nan
        if len(vals) and float(vals.max()) > best_score:
            best_score = float(vals.max())
            idx = eligible[col].abs().idxmax()
            best_coord = eligible.loc[idx, "coordinate"]
            best_quantity = quantity
    result["best_coordinate"] = best_coord
    result["best_quantity"] = best_quantity
    result["best_abs_difference"] = best_score if best_score >= 0 else np.nan
    return result


def plot_diff_heatmap(diff: pd.DataFrame, quantities: list[str], title: str, path: Path, max_rows: int = 32) -> None:
    work = diff.copy()
    if len(work) > max_rows:
        work["_score"] = work[[f"miss_minus_control_{q}" for q in quantities]].abs().max(axis=1)
        top = set(work.sort_values("_score", ascending=False).head(max_rows)["coordinate"].tolist())
        work = work[work["coordinate"].isin(top)].sort_values("coordinate")
    cols = [f"miss_minus_control_{q}" for q in quantities]
    vals = work[cols].to_numpy(dtype=float)
    max_abs = np.nanmax(np.abs(vals)) if np.isfinite(vals).any() else 1.0
    max_abs = max(max_abs, 1.0)
    cell_w, cell_h = 185, 38
    left, top = 185, 125
    width = left + cell_w * len(cols) + 80
    height = top + cell_h * len(work) + 100
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    draw.text((55, 35), title, fill="#1e2a33", font=font(28, True))
    draw.text((55, 72), "Cells are median miss-control differences at the same alignment coordinate.", fill="#4a5963", font=font(15))
    for j, col in enumerate(cols):
        label = col.replace("miss_minus_control_", "")
        draw.text((left + j * cell_w + 4, top - 34), label[:22], fill="#1e2a33", font=font(13, True))
    for i, row in enumerate(work.itertuples(index=False)):
        y = top + i * cell_h
        draw.text((55, y + 10), str(getattr(row, "coordinate")), fill="#1e2a33", font=font(12))
        for j, col in enumerate(cols):
            val = getattr(row, col)
            x = left + j * cell_w
            if pd.isna(val):
                color, txt = "#f0f0f0", "NA"
            elif val >= 0:
                color, txt = blend_hex(COLORS["neutral"], COLORS["positive"], min(1, abs(val) / max_abs)), f"{val:.1f}"
            else:
                color, txt = blend_hex(COLORS["neutral"], COLORS["negative"], min(1, abs(val) / max_abs)), f"{val:.1f}"
            draw.rectangle((x, y, x + cell_w - 2, y + cell_h - 2), fill=color, outline="#d7dde2")
            draw.text((x + 70, y + 10), txt, fill="#17232c", font=font(12))
    img.save(path)


def paired_start_differences(aligned: pd.DataFrame, candidates: pd.DataFrame) -> pd.DataFrame:
    start = add_start_index(aligned)
    lookup = {
        key: sub.set_index("start_step_index").copy()
        for key, sub in start.groupby(["sample_id", "trajectory_id"], sort=False)
    }
    rows = []
    for idx, cand in candidates.iterrows():
        mkey = (cand["miss_sample_id"], cand["miss_trajectory_id"])
        ckey = (cand["control_sample_id"], cand["control_trajectory_id"])
        if mkey not in lookup or ckey not in lookup:
            continue
        miss = lookup[mkey]
        control = lookup[ckey]
        coords = sorted(set(miss.index).union(control.index))
        for coord in coords:
            row = {
                "pair_id": idx + 1,
                "start_step_index": int(coord),
                "miss_sample_id": cand["miss_sample_id"],
                "miss_trajectory_id": cand["miss_trajectory_id"],
                "control_sample_id": cand["control_sample_id"],
                "control_trajectory_id": cand["control_trajectory_id"],
            }
            for quantity in ["R_before", "R_drop", "transition_k", "exit_distance"]:
                mv = miss.loc[coord, quantity] if coord in miss.index else np.nan
                cv = control.loc[coord, quantity] if coord in control.index else np.nan
                row[f"miss_{quantity}"] = mv
                row[f"control_{quantity}"] = cv
                row[f"delta_{quantity}"] = mv - cv if pd.notna(mv) and pd.notna(cv) else np.nan
            rows.append(row)
    return pd.DataFrame(rows)


def write_report(signal: pd.DataFrame, notable: dict[str, pd.DataFrame]) -> None:
    def markdown_table(df: pd.DataFrame) -> str:
        small = df.head(12).copy()
        cols = small.columns.tolist()
        lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
        for row in small.itertuples(index=False):
            vals = []
            for value in row:
                if isinstance(value, float):
                    vals.append("NA" if pd.isna(value) else f"{value:.3g}")
                else:
                    vals.append(str(value))
            lines.append("| " + " | ".join(vals) + " |")
        return "\n".join(lines)

    lines = []
    lines.append("# Alignment Coordinate Comparison")
    lines.append("")
    lines.append("finite-sample observational note: this report changes the alignment coordinate while keeping the same observed numeric rows.")
    lines.append("")
    lines.append("## Motivation")
    lines.append("")
    lines.append("The paired-difference audit showed that several variables collapse together under terminal suffix matching. This pass asks whether the view changes when the same data are aligned by start step, terminal step, exit_distance, or R_before.")
    lines.append("")
    lines.append("## Coordinate Signal Table")
    lines.append("")
    lines.append("| alignment | eligible_coordinate_count | best_coordinate | best_quantity | best_abs_difference |")
    lines.append("|---|---:|---:|---|---:|")
    for r in signal.itertuples(index=False):
        lines.append(f"| {r.alignment} | {int(r.eligible_coordinate_count)} | {r.best_coordinate} | {r.best_quantity} | {float(r.best_abs_difference):.2f} |")
    lines.append("")
    lines.append("## Readout")
    lines.append("")
    lines.append("Terminal alignment makes the last steps collapse, which is useful for seeing local deformation before convergence. Start alignment asks where the traces begin to separate from the entry side. Exit-distance and R_before alignment change the question from trajectory time to coordinate slices: what do miss/control rows look like at the same location in the local coordinate system?")
    lines.append("")
    for name, df in notable.items():
        lines.append(f"## {name}")
        lines.append("")
        lines.append(markdown_table(df))
        lines.append("")
    lines.append("finite-sample observational note: these tables compare coordinate views only; they do not assert a mechanism.")
    lines.append("")
    lines.append("## Output files")
    lines.append("")
    for filename in [
        "alignment_coordinate_signal_table.csv",
        "terminal_alignment_difference_summary.csv",
        "start_alignment_difference_summary.csv",
        "exit_distance_alignment_difference_summary.csv",
        "R_before_alignment_difference_summary.csv",
        "paired_start_aligned_differences.csv",
        "terminal_alignment_heatmap.png",
        "start_alignment_heatmap.png",
        "exit_distance_alignment_heatmap.png",
        "R_before_alignment_heatmap.png",
    ]:
        lines.append(f"- `{filename}`")
    (OUT / "alignment_coordinate_comparison_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    aligned = pd.read_csv(IN / "aligned_numeric_paths.csv")
    aligned["group"] = aligned.apply(group_name, axis=1)
    start = add_start_index(aligned)
    candidates = pd.read_csv(IN / "route_difference_candidates.csv")

    terminal_quantities = ["R_before", "R_drop", "transition_k", "exit_distance"]
    coordinate_quantities = ["R_before", "R_drop", "transition_k", "exit_distance"]
    terminal_summary = summarize_by_axis(aligned, "reverse_step_index", terminal_quantities)
    terminal_diff = diff_from_summary(terminal_summary, terminal_quantities)
    start_summary = summarize_by_axis(start, "start_step_index", coordinate_quantities)
    start_diff = diff_from_summary(start_summary, coordinate_quantities)
    exit_summary = summarize_by_axis(aligned, "exit_distance", ["R_before", "R_drop", "transition_k"])
    exit_diff = diff_from_summary(exit_summary, ["R_before", "R_drop", "transition_k"])
    r_summary = summarize_by_axis(aligned, "R_before", ["R_drop", "transition_k", "exit_distance"])
    r_diff = diff_from_summary(r_summary, ["R_drop", "transition_k", "exit_distance"])
    start_pairs = paired_start_differences(aligned, candidates)

    terminal_summary.to_csv(OUT / "terminal_alignment_group_summary.csv", index=False, encoding="utf-8")
    start_summary.to_csv(OUT / "start_alignment_group_summary.csv", index=False, encoding="utf-8")
    exit_summary.to_csv(OUT / "exit_distance_alignment_group_summary.csv", index=False, encoding="utf-8")
    r_summary.to_csv(OUT / "R_before_alignment_group_summary.csv", index=False, encoding="utf-8")
    terminal_diff.to_csv(OUT / "terminal_alignment_difference_summary.csv", index=False, encoding="utf-8")
    start_diff.to_csv(OUT / "start_alignment_difference_summary.csv", index=False, encoding="utf-8")
    exit_diff.to_csv(OUT / "exit_distance_alignment_difference_summary.csv", index=False, encoding="utf-8")
    r_diff.to_csv(OUT / "R_before_alignment_difference_summary.csv", index=False, encoding="utf-8")
    start_pairs.to_csv(OUT / "paired_start_aligned_differences.csv", index=False, encoding="utf-8")

    signal_rows = [
        compact_signal(terminal_diff, terminal_quantities),
        compact_signal(start_diff, coordinate_quantities),
        compact_signal(exit_diff, ["R_before", "R_drop", "transition_k"]),
        compact_signal(r_diff, ["R_drop", "transition_k", "exit_distance"]),
    ]
    signal = pd.DataFrame(signal_rows)
    signal.to_csv(OUT / "alignment_coordinate_signal_table.csv", index=False, encoding="utf-8")

    plot_diff_heatmap(terminal_diff, terminal_quantities, "Terminal-aligned miss-control differences", OUT / "terminal_alignment_heatmap.png")
    plot_diff_heatmap(start_diff, coordinate_quantities, "Start-aligned miss-control differences", OUT / "start_alignment_heatmap.png")
    plot_diff_heatmap(exit_diff, ["R_before", "R_drop", "transition_k"], "Exit-distance-aligned miss-control differences", OUT / "exit_distance_alignment_heatmap.png")
    plot_diff_heatmap(r_diff, ["R_drop", "transition_k", "exit_distance"], "R_before-aligned miss-control differences", OUT / "R_before_alignment_heatmap.png")

    notable = {
        "Top terminal coordinates": terminal_diff.assign(score=terminal_diff[[f"miss_minus_control_{q}" for q in terminal_quantities]].abs().max(axis=1)).sort_values("score", ascending=False),
        "Top start coordinates": start_diff.assign(score=start_diff[[f"miss_minus_control_{q}" for q in coordinate_quantities]].abs().max(axis=1)).sort_values("score", ascending=False),
        "Top exit_distance coordinates": exit_diff.assign(score=exit_diff[[f"miss_minus_control_{q}" for q in ["R_before", "R_drop", "transition_k"]]].abs().max(axis=1)).sort_values("score", ascending=False),
        "Top R_before coordinates": r_diff.assign(score=r_diff[[f"miss_minus_control_{q}" for q in ["R_drop", "transition_k", "exit_distance"]]].abs().max(axis=1)).sort_values("score", ascending=False),
    }
    write_report(signal, notable)
    meta = {
        "terminal_coordinates": int(len(terminal_diff)),
        "start_coordinates": int(len(start_diff)),
        "exit_distance_coordinates": int(len(exit_diff)),
        "R_before_coordinates": int(len(r_diff)),
        "paired_start_rows": int(len(start_pairs)),
        "output_dir": str(OUT),
    }
    (OUT / "run_summary.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
