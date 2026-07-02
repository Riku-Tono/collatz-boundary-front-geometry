from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageColor, ImageDraw, ImageFont


ROOT = Path(r"C:\Users\yauki\Documents\Codex\2026-07-01\csv-collatz-state-band-boundary-front")
IN = ROOT / "outputs" / "numeric_trajectory_anatomy"
OUT = ROOT / "outputs" / "paired_numeric_difference_map"

QUANTITIES = ["R_before", "R_drop", "transition_k", "exit_distance"]


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


def pair_key(row: pd.Series) -> str:
    return (
        f"{row['miss_sample_id']}:{row['miss_trajectory_id']}__"
        f"{row['control_sample_id']}:{row['control_trajectory_id']}"
    )


def load_pair_paths() -> pd.DataFrame:
    candidates = pd.read_csv(IN / "route_difference_candidates.csv")
    aligned = pd.read_csv(IN / "aligned_numeric_paths.csv")
    lookup = {
        (row.sample_id, row.trajectory_id): sub.copy()
        for (row), sub in []
    }
    lookup = {
        key: sub.sort_values("reverse_step_index").copy()
        for key, sub in aligned.groupby(["sample_id", "trajectory_id"], sort=False)
    }

    rows = []
    for idx, cand in candidates.iterrows():
        mkey = (cand["miss_sample_id"], cand["miss_trajectory_id"])
        ckey = (cand["control_sample_id"], cand["control_trajectory_id"])
        if mkey not in lookup or ckey not in lookup:
            continue
        miss = lookup[mkey].set_index("reverse_step_index")
        control = lookup[ckey].set_index("reverse_step_index")
        revs = sorted(set(miss.index).union(control.index))
        pkey = pair_key(cand)
        for rev in revs:
            row = {
                "pair_id": idx + 1,
                "pair_key": pkey,
                "miss_sample_id": cand["miss_sample_id"],
                "miss_trajectory_id": cand["miss_trajectory_id"],
                "control_sample_id": cand["control_sample_id"],
                "control_trajectory_id": cand["control_trajectory_id"],
                "shared_suffix_length": cand["shared_suffix_length"],
                "reverse_step_index": int(rev),
            }
            for quantity in QUANTITIES:
                mv = miss.loc[rev, quantity] if rev in miss.index else np.nan
                cv = control.loc[rev, quantity] if rev in control.index else np.nan
                row[f"miss_{quantity}"] = mv
                row[f"control_{quantity}"] = cv
                row[f"delta_{quantity}"] = mv - cv if pd.notna(mv) and pd.notna(cv) else np.nan
            rows.append(row)
    return pd.DataFrame(rows)


def add_change_differences(paths: pd.DataFrame) -> pd.DataFrame:
    out = paths.sort_values(["pair_id", "reverse_step_index"]).copy()
    for quantity in QUANTITIES:
        out[f"miss_d_{quantity}"] = out.groupby("pair_id")[f"miss_{quantity}"].diff()
        out[f"control_d_{quantity}"] = out.groupby("pair_id")[f"control_{quantity}"].diff()
        out[f"delta_d_{quantity}"] = out[f"miss_d_{quantity}"] - out[f"control_d_{quantity}"]
    return out


def summarize(paths: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for rev, sub in paths.groupby("reverse_step_index"):
        row = {"reverse_step_index": int(rev), "pair_count": int(sub["pair_id"].nunique())}
        for quantity in QUANTITIES:
            vals = pd.to_numeric(sub[f"delta_{quantity}"], errors="coerce").dropna()
            dvals = pd.to_numeric(sub[f"delta_d_{quantity}"], errors="coerce").dropna()
            row[f"median_delta_{quantity}"] = float(vals.median()) if len(vals) else np.nan
            row[f"q25_delta_{quantity}"] = float(vals.quantile(0.25)) if len(vals) else np.nan
            row[f"q75_delta_{quantity}"] = float(vals.quantile(0.75)) if len(vals) else np.nan
            row[f"median_change_delta_{quantity}"] = float(dvals.median()) if len(dvals) else np.nan
            row[f"abs_median_delta_{quantity}"] = abs(row[f"median_delta_{quantity}"]) if pd.notna(row[f"median_delta_{quantity}"]) else np.nan
        rows.append(row)
    return pd.DataFrame(rows).sort_values("reverse_step_index")


def local_jump_signature(paths: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for pid, sub in paths.groupby("pair_id"):
        row = sub.iloc[0]
        best = None
        for r in sub.itertuples(index=False):
            score = 0.0
            parts = {}
            for quantity in QUANTITIES:
                val = getattr(r, f"delta_d_{quantity}")
                parts[f"jump_delta_{quantity}"] = val
                if pd.notna(val):
                    score += abs(float(val))
            if best is None or score > best[0]:
                best = (score, r.reverse_step_index, parts)
        if best is None:
            continue
        score, rev, parts = best
        rows.append(
            {
                "pair_id": int(pid),
                "miss_sample_id": row["miss_sample_id"],
                "miss_trajectory_id": row["miss_trajectory_id"],
                "control_sample_id": row["control_sample_id"],
                "control_trajectory_id": row["control_trajectory_id"],
                "max_jump_reverse_step_index": int(rev),
                "max_jump_score": float(score),
                **parts,
            }
        )
    return pd.DataFrame(rows).sort_values("max_jump_score", ascending=False)


def plot_difference_overlay(paths: pd.DataFrame, quantity: str, path: Path) -> None:
    width, height = 1600, 950
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    title_font = font(30, True)
    label_font = font(15)
    small = font(12)
    draw.text((60, 35), f"Paired difference: miss - control ({quantity})", fill="#1e2a33", font=title_font)
    draw.text((60, 75), "Thin lines are suffix-matched pairs; thick line is median delta by reverse index.", fill="#4a5963", font=label_font)
    l, t, r, b = 120, 130, width - 80, height - 110
    col = f"delta_{quantity}"
    xvals = sorted(paths["reverse_step_index"].unique())
    vals = pd.to_numeric(paths[col], errors="coerce").dropna()
    ymin, ymax = float(vals.quantile(0.02)), float(vals.quantile(0.98))
    ymax = max(abs(ymin), abs(ymax), 1.0)
    ymin = -ymax
    draw.rectangle((l, t, r, b), outline="#303b44", width=2)
    zero_y = b - (0 - ymin) / (ymax - ymin) * (b - t)
    draw.line((l, zero_y, r, zero_y), fill="#1e2a33", width=2)
    for frac in np.linspace(0, 1, 5):
        y = b - frac * (b - t)
        val = ymin + frac * (ymax - ymin)
        draw.line((l, y, r, y), fill="#e1e7ec", width=1)
        draw.text((l - 62, y - 8), f"{val:.1f}", fill="#46535c", font=small)
    for x in xvals:
        xp = l + (x - min(xvals)) / max(1, max(xvals) - min(xvals)) * (r - l)
        draw.line((xp, b, xp, b + 5), fill="#303b44", width=1)
        draw.text((xp - 9, b + 12), str(x), fill="#46535c", font=small)

    def pt(x: int, yv: float) -> tuple[float, float]:
        xp = l + (x - min(xvals)) / max(1, max(xvals) - min(xvals)) * (r - l)
        yp = b - (yv - ymin) / (ymax - ymin) * (b - t)
        return xp, max(t, min(b, yp))

    for _, sub in paths.groupby("pair_id"):
        sub = sub.sort_values("reverse_step_index")
        pts = [(int(row.reverse_step_index), getattr(row, col)) for row in sub.itertuples(index=False) if pd.notna(getattr(row, col))]
        if len(pts) >= 2:
            draw.line([pt(x, float(yv)) for x, yv in pts], fill="#c9cfd5", width=1)
    med = paths.groupby("reverse_step_index")[col].median().dropna()
    pts = [(int(x), float(v)) for x, v in med.items()]
    if len(pts) >= 2:
        draw.line([pt(x, yv) for x, yv in pts], fill="#b9413b", width=5)
    draw.text((l, b + 48), "reverse_step_index (terminal = 0)", fill="#1e2a33", font=label_font)
    img.save(path)


def plot_heatmap(summary: pd.DataFrame, path: Path) -> None:
    cols = [
        "median_delta_R_before",
        "median_delta_R_drop",
        "median_delta_transition_k",
        "median_delta_exit_distance",
        "median_change_delta_R_before",
        "median_change_delta_R_drop",
        "median_change_delta_transition_k",
        "median_change_delta_exit_distance",
    ]
    cell_w, cell_h = 160, 40
    left, top = 185, 130
    width = left + cell_w * len(cols) + 80
    height = top + cell_h * len(summary) + 90
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    draw.text((55, 35), "Paired difference heatmap", fill="#1e2a33", font=font(28, True))
    draw.text((55, 72), "Cells show median miss-control differences; change columns compare step-to-step movement.", fill="#4a5963", font=font(15))
    vals = summary[cols].to_numpy(dtype=float)
    max_abs = np.nanmax(np.abs(vals)) if np.isfinite(vals).any() else 1.0
    max_abs = max(max_abs, 1.0)
    for j, col in enumerate(cols):
        label = col.replace("median_", "").replace("delta_", "d_").replace("transition_k", "k")
        draw.text((left + j * cell_w + 4, top - 45), label[:18], fill="#1e2a33", font=font(12, True))
    for i, row in enumerate(summary.itertuples(index=False)):
        y = top + i * cell_h
        draw.text((55, y + 10), str(int(row.reverse_step_index)), fill="#1e2a33", font=font(13))
        for j, col in enumerate(cols):
            val = getattr(row, col)
            x = left + j * cell_w
            if pd.isna(val):
                color, txt = "#f0f0f0", "NA"
            elif val >= 0:
                color, txt = blend_hex("#f8f8fb", "#bd3f3b", min(1, abs(val) / max_abs)), f"{val:.1f}"
            else:
                color, txt = blend_hex("#f8f8fb", "#256fa8", min(1, abs(val) / max_abs)), f"{val:.1f}"
            draw.rectangle((x, y, x + cell_w - 2, y + cell_h - 2), fill=color, outline="#d7dde2")
            draw.text((x + 55, y + 11), txt, fill="#17232c", font=font(12))
    img.save(path)


def write_report(paths: pd.DataFrame, summary: pd.DataFrame, jumps: pd.DataFrame) -> None:
    lines = []
    lines.append("# Paired Numeric Difference Map")
    lines.append("")
    lines.append("finite-sample observational note: this report looks only at observed suffix-matched miss/control numeric differences.")
    lines.append("")
    lines.append("## What Changed")
    lines.append("")
    lines.append("The previous view showed raw numeric paths. This view subtracts the matched control from the miss trajectory at each terminal-aligned reverse index, so the object is the local difference itself.")
    lines.append("")
    lines.append("## Difference Summary")
    lines.append("")
    lines.append(f"The map contains {paths['pair_id'].nunique():,} miss/control pairs and {len(paths):,} aligned pair-step rows. Positive values mean the miss trajectory is higher than its matched control at the same terminal-aligned index.")
    lines.append("")
    lines.append("| reverse_step_index | pair_count | median_delta_R_before | median_delta_R_drop | median_delta_k | median_delta_exit_distance |")
    lines.append("|---:|---:|---:|---:|---:|---:|")
    for r in summary.itertuples(index=False):
        lines.append(
            f"| {int(r.reverse_step_index)} | {int(r.pair_count)} | "
            f"{r.median_delta_R_before:.1f} | {r.median_delta_R_drop:.1f} | "
            f"{r.median_delta_transition_k:.1f} | {r.median_delta_exit_distance:.1f} |"
        )
    lines.append("")
    lines.append("## Local Jump Candidates")
    lines.append("")
    lines.append("The strongest local jumps are where the step-to-step movement difference is largest across the four numeric quantities.")
    lines.append("")
    lines.append("| miss_trajectory | control_trajectory | max_jump_reverse_step_index | max_jump_score | d_R_before | d_R_drop | d_k | d_exit_distance |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|")
    for r in jumps.head(12).itertuples(index=False):
        lines.append(
            f"| `{r.miss_sample_id}:{r.miss_trajectory_id}` | `{r.control_sample_id}:{r.control_trajectory_id}` | "
            f"{int(r.max_jump_reverse_step_index)} | {float(r.max_jump_score):.1f} | "
            f"{float(r.jump_delta_R_before):.1f} | {float(r.jump_delta_R_drop):.1f} | "
            f"{float(r.jump_delta_transition_k):.1f} | {float(r.jump_delta_exit_distance):.1f} |"
        )
    lines.append("")
    lines.append("## Reading")
    lines.append("")
    lines.append("The difference view supports the small-but-local picture: many terminal positions collapse back toward zero, while the earlier aligned steps carry the visible miss/control separation. This is closer to a local deformation of a shared road than to a separate route class.")
    lines.append("")
    lines.append("finite-sample observational note: these are difference maps for the available paired rows only, not a proof or mechanism.")
    lines.append("")
    lines.append("## Output files")
    lines.append("")
    for name in [
        "paired_numeric_differences.csv",
        "paired_numeric_difference_summary.csv",
        "local_jump_signature_table.csv",
        "paired_R_before_difference.png",
        "paired_R_drop_difference.png",
        "paired_k_difference.png",
        "paired_exit_distance_difference.png",
        "paired_difference_heatmap.png",
    ]:
        lines.append(f"- `{name}`")
    (OUT / "paired_numeric_difference_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    paths = add_change_differences(load_pair_paths())
    summary = summarize(paths)
    jumps = local_jump_signature(paths)
    paths.to_csv(OUT / "paired_numeric_differences.csv", index=False, encoding="utf-8")
    summary.to_csv(OUT / "paired_numeric_difference_summary.csv", index=False, encoding="utf-8")
    jumps.to_csv(OUT / "local_jump_signature_table.csv", index=False, encoding="utf-8")
    plot_difference_overlay(paths, "R_before", OUT / "paired_R_before_difference.png")
    plot_difference_overlay(paths, "R_drop", OUT / "paired_R_drop_difference.png")
    plot_difference_overlay(paths, "transition_k", OUT / "paired_k_difference.png")
    plot_difference_overlay(paths, "exit_distance", OUT / "paired_exit_distance_difference.png")
    plot_heatmap(summary, OUT / "paired_difference_heatmap.png")
    write_report(paths, summary, jumps)
    meta = {
        "pair_count": int(paths["pair_id"].nunique()),
        "aligned_pair_step_rows": int(len(paths)),
        "output_dir": str(OUT),
    }
    (OUT / "run_summary.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
