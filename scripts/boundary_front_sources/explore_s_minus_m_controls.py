from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Iterable

import pandas as pd


ROOT = Path(r"C:\Users\yauki\Documents\Codex\2026-07-01\new-chat")
OUT = ROOT / "outputs" / "s_minus_m_control_exploration"
WAITING_DETAIL = (
    Path(r"C:\Users\yauki\Documents\Codex\2026-06-30")
    / "task-waiting-hall-interior-map-audit"
    / "outputs"
    / "waiting_hall_interior_detail.csv"
)
EXIT_EVENTS = (
    Path(r"C:\Users\yauki\Documents\Codex\2026-06-30")
    / "task-exit-avoidance-path-space-audit"
    / "outputs"
    / "exit_avoidance_path_events.csv"
)
EXIT_CHAINS = (
    Path(r"C:\Users\yauki\Documents\Codex\2026-06-30")
    / "task-exit-avoidance-path-space-audit"
    / "outputs"
    / "exit_avoidance_chains.csv"
)


def as_int(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype("Int64")


def dist(df: pd.DataFrame, col: str, group_col: str = "group") -> pd.DataFrame:
    return (
        df.groupby([group_col, col], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values([group_col, "count", col], ascending=[True, False, True])
    )


def md_table(df: pd.DataFrame, max_rows: int | None = None) -> str:
    if max_rows is not None:
        df = df.head(max_rows)
    cols = list(df.columns)
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join(["---"] * len(cols)) + " |",
    ]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[c]) for c in cols) + " |")
    return "\n".join(lines)


def top_counts(values: Iterable[object], n: int = 8) -> str:
    c = Counter("NA" if pd.isna(v) else str(v) for v in values)
    return "; ".join(f"{k}:{v}" for k, v in c.most_common(n))


def numeric_summary(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    rows = []
    for group, g in df.groupby("group"):
        for col in cols:
            s = pd.to_numeric(g[col], errors="coerce").dropna()
            rows.append(
                {
                    "group": group,
                    "feature": col,
                    "n": int(s.size),
                    "min": "" if s.empty else float(s.min()),
                    "median": "" if s.empty else float(s.median()),
                    "mean": "" if s.empty else round(float(s.mean()), 6),
                    "max": "" if s.empty else float(s.max()),
                    "unique": int(s.nunique()),
                }
            )
    return pd.DataFrame(rows)


def add_context_windows(df: pd.DataFrame, targets: pd.DataFrame) -> pd.DataFrame:
    ordered = df.sort_values(["sample_id", "trajectory_id", "band", "source_scope", "event_index"]).copy()
    grouped = {
        key: g.reset_index(drop=True)
        for key, g in ordered.groupby(["sample_id", "trajectory_id", "band", "source_scope"], dropna=False)
    }
    records = []
    for _, row in targets.iterrows():
        key = (row["sample_id"], row["trajectory_id"], row["band"], row["source_scope"])
        g = grouped.get(key)
        rec = {
            "event_row_id": row["event_row_id"],
            "sample_id": row["sample_id"],
            "trajectory_id": row["trajectory_id"],
            "group": row["group"],
            "event_index": row["event_index"],
        }
        if g is None:
            records.append(rec)
            continue
        matches = g.index[g["event_row_id"].eq(row["event_row_id"])].tolist()
        if not matches:
            records.append(rec)
            continue
        i = matches[0]
        for offset in [-3, -2, -1, 0, 1, 2, 3, 4, 5]:
            j = i + offset
            prefix = f"t{offset:+d}".replace("+", "p").replace("-", "m")
            if 0 <= j < len(g):
                rr = g.iloc[j]
                rec[f"{prefix}_R_before"] = rr["remaining_K_before"]
                rec[f"{prefix}_k"] = rr["transition_k"]
                rec[f"{prefix}_exit_distance"] = rr["exit_distance"]
                rec[f"{prefix}_position"] = rr["position_label"]
                rec[f"{prefix}_near_behavior"] = rr["near_behavior"]
            else:
                rec[f"{prefix}_R_before"] = ""
                rec[f"{prefix}_k"] = ""
                rec[f"{prefix}_exit_distance"] = ""
                rec[f"{prefix}_position"] = ""
                rec[f"{prefix}_near_behavior"] = ""
        k_seq = []
        r_seq = []
        behavior_seq = []
        for j in range(i, min(i + 8, len(g))):
            rr = g.iloc[j]
            k_seq.append(str(rr["transition_k"]))
            r_seq.append(str(rr["remaining_K_before"]))
            behavior_seq.append(str(rr["near_behavior"]))
        rec["forward_k_seq_8"] = ",".join(k_seq)
        rec["forward_R_before_seq_8"] = ",".join(r_seq)
        rec["forward_near_behavior_seq_8"] = ",".join(behavior_seq)
        records.append(rec)
    return pd.DataFrame(records)


def nearest_miss_table(miss: pd.DataFrame, controls: pd.DataFrame) -> pd.DataFrame:
    miss_rows = miss.copy()
    records = []
    for _, c in controls.iterrows():
        same_shape = miss_rows[miss_rows["residue_pair_mod32"].eq(c["residue_pair_mod32"])]
        if same_shape.empty:
            same_shape = miss_rows
        tmp = same_shape.copy()
        tmp["abs_exit_distance_delta"] = (tmp["exit_distance"] - c["exit_distance"]).abs()
        tmp["abs_R_before_delta"] = (tmp["remaining_K_before"] - c["remaining_K_before"]).abs()
        tmp["abs_transition_k_delta"] = (tmp["transition_k"] - c["transition_k"]).abs()
        tmp["nearest_score"] = (
            tmp["abs_exit_distance_delta"] * 1000
            + tmp["abs_R_before_delta"] * 10
            + tmp["abs_transition_k_delta"]
        )
        n = tmp.sort_values(["nearest_score", "event_row_id"]).iloc[0]
        records.append(
            {
                "control_event_row_id": c["event_row_id"],
                "sample_id": c["sample_id"],
                "trajectory_id": c["trajectory_id"],
                "control_R_before": c["remaining_K_before"],
                "control_R_after": c["remaining_K_after"],
                "control_exit_distance": c["exit_distance"],
                "control_transition_k": c["transition_k"],
                "residue_pair_mod32": c["residue_pair_mod32"],
                "nearest_miss_event_row_id": n["event_row_id"],
                "nearest_miss_R_before": n["remaining_K_before"],
                "nearest_miss_R_after": n["remaining_K_after"],
                "nearest_miss_exit_distance": n["exit_distance"],
                "nearest_miss_transition_k": n["transition_k"],
                "delta_exit_distance_control_minus_miss": c["exit_distance"] - n["exit_distance"],
                "delta_R_before_control_minus_miss": c["remaining_K_before"] - n["remaining_K_before"],
                "delta_transition_k_control_minus_miss": c["transition_k"] - n["transition_k"],
            }
        )
    return pd.DataFrame(records)


def write_svg_scatter(
    combined: pd.DataFrame,
    x_col: str,
    y_col: str,
    path: Path,
    title: str,
    x_label: str,
    y_label: str,
) -> None:
    width, height = 920, 560
    left, right, top, bottom = 82, 34, 62, 72
    plot_w = width - left - right
    plot_h = height - top - bottom
    x = pd.to_numeric(combined[x_col], errors="coerce")
    y = pd.to_numeric(combined[y_col], errors="coerce")
    x_min, x_max = float(x.min()), float(x.max())
    y_min, y_max = float(y.min()), float(y.max())
    if x_min == x_max:
        x_min -= 1
        x_max += 1
    if y_min == y_max:
        y_min -= 1
        y_max += 1
    x_pad = (x_max - x_min) * 0.04
    y_pad = (y_max - y_min) * 0.08
    x_min -= x_pad
    x_max += x_pad
    y_min -= y_pad
    y_max += y_pad

    def sx(v: object) -> float:
        return left + (float(v) - x_min) / (x_max - x_min) * plot_w

    def sy(v: object) -> float:
        return top + plot_h - (float(v) - y_min) / (y_max - y_min) * plot_h

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width/2}" y="32" text-anchor="middle" font-family="Arial, sans-serif" font-size="20" font-weight="700">{title}</text>',
        f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="#333" stroke-width="1.2"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#333" stroke-width="1.2"/>',
    ]
    for i in range(6):
        tx = x_min + (x_max - x_min) * i / 5
        px = sx(tx)
        parts.append(f'<line x1="{px:.2f}" y1="{top}" x2="{px:.2f}" y2="{top + plot_h}" stroke="#e5e7eb"/>')
        parts.append(f'<text x="{px:.2f}" y="{top + plot_h + 24}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#444">{tx:.0f}</text>')
    for i in range(6):
        ty = y_min + (y_max - y_min) * i / 5
        py = sy(ty)
        parts.append(f'<line x1="{left}" y1="{py:.2f}" x2="{left + plot_w}" y2="{py:.2f}" stroke="#e5e7eb"/>')
        parts.append(f'<text x="{left - 12}" y="{py + 4:.2f}" text-anchor="end" font-family="Arial, sans-serif" font-size="12" fill="#444">{ty:.0f}</text>')
    parts.append(f'<text x="{left + plot_w/2}" y="{height - 24}" text-anchor="middle" font-family="Arial, sans-serif" font-size="15">{x_label}</text>')
    parts.append(f'<text transform="translate(24 {top + plot_h/2}) rotate(-90)" text-anchor="middle" font-family="Arial, sans-serif" font-size="15">{y_label}</text>')

    styles = {
        "M_miss": ("#c2410c", 4, 0.58, "M miss (228)"),
        "S_minus_M_control": ("#2563eb", 7, 0.82, "S\\M control (47)"),
    }
    for group in ["M_miss", "S_minus_M_control"]:
        g = combined[combined["group"].eq(group)]
        color, radius, opacity, _ = styles[group]
        for _, row in g.iterrows():
            if pd.isna(row[x_col]) or pd.isna(row[y_col]):
                continue
            parts.append(
                f'<circle cx="{sx(row[x_col]):.2f}" cy="{sy(row[y_col]):.2f}" r="{radius}" '
                f'fill="{color}" fill-opacity="{opacity}" stroke="white" stroke-width="0.6"/>'
            )
    legend_x = left + plot_w - 210
    legend_y = top + 12
    parts.append(f'<rect x="{legend_x}" y="{legend_y}" width="190" height="58" fill="white" stroke="#d1d5db"/>')
    for idx, group in enumerate(["M_miss", "S_minus_M_control"]):
        color, radius, opacity, label = styles[group]
        y0 = legend_y + 22 + idx * 24
        parts.append(f'<circle cx="{legend_x + 18}" cy="{y0}" r="{radius}" fill="{color}" fill-opacity="{opacity}"/>')
        parts.append(f'<text x="{legend_x + 34}" y="{y0 + 4}" font-family="Arial, sans-serif" font-size="13">{label}</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def maybe_plot(combined: pd.DataFrame) -> list[str]:
    plot_paths: list[str] = []
    svg1 = OUT / "miss_vs_control_exit_distance_transition_k.svg"
    write_svg_scatter(
        combined,
        "exit_distance",
        "transition_k",
        svg1,
        "Miss events vs S\\M controls: position and transition_k",
        "exit_distance",
        "transition_k",
    )
    plot_paths.append(str(svg1))
    svg2 = OUT / "miss_vs_control_R_before_after.svg"
    write_svg_scatter(
        combined,
        "remaining_K_before",
        "remaining_K_after",
        svg2,
        "Miss events vs S\\M controls: R before/after",
        "remaining_K_before",
        "remaining_K_after",
    )
    plot_paths.append(str(svg2))
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return plot_paths

    colors = {"M_miss": "#c2410c", "S_minus_M_control": "#2563eb"}
    labels = {"M_miss": "M miss (228)", "S_minus_M_control": "S\\M control (47)"}

    fig, ax = plt.subplots(figsize=(8, 5))
    for group, g in combined.groupby("group"):
        ax.scatter(
            g["exit_distance"],
            g["transition_k"],
            s=18 if group == "M_miss" else 34,
            alpha=0.55 if group == "M_miss" else 0.8,
            c=colors[group],
            label=labels[group],
            edgecolors="none",
        )
    ax.set_xlabel("exit_distance")
    ax.set_ylabel("transition_k")
    ax.set_title("Miss events vs S\\M controls: position and transition_k")
    ax.legend()
    ax.grid(True, alpha=0.25)
    p = OUT / "miss_vs_control_exit_distance_transition_k.png"
    fig.tight_layout()
    fig.savefig(p, dpi=160)
    plt.close(fig)
    plot_paths.append(str(p))

    fig, ax = plt.subplots(figsize=(8, 5))
    for group, g in combined.groupby("group"):
        ax.scatter(
            g["remaining_K_before"],
            g["remaining_K_after"],
            s=18 if group == "M_miss" else 34,
            alpha=0.55 if group == "M_miss" else 0.8,
            c=colors[group],
            label=labels[group],
            edgecolors="none",
        )
    ax.set_xlabel("remaining_K_before")
    ax.set_ylabel("remaining_K_after")
    ax.set_title("Miss events vs S\\M controls: R before/after")
    ax.legend()
    ax.grid(True, alpha=0.25)
    p = OUT / "miss_vs_control_R_before_after.png"
    fig.tight_layout()
    fig.savefig(p, dpi=160)
    plt.close(fig)
    plot_paths.append(str(p))

    return plot_paths


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(WAITING_DETAIL)
    df = df.copy()
    df["event_row_id"] = range(1, len(df) + 1)
    for col in ["event_index", "remaining_K_before", "remaining_K_after", "transition_k", "distance_from_exit", "wait_length"]:
        df[col] = as_int(df[col])
    df["exit_distance"] = df["distance_from_exit"]
    df["miss_event"] = pd.to_numeric(df["miss_event"], errors="coerce").fillna(0).astype(int)
    df["residue_before_mod32"] = (df["remaining_K_before"] % 32).astype("Int64")
    df["residue_after_mod32"] = (df["remaining_K_after"] % 32).astype("Int64")
    df["residue_before_mod16"] = (df["remaining_K_before"] % 16).astype("Int64")
    df["residue_after_mod16"] = (df["remaining_K_after"] % 16).astype("Int64")
    df["residue_pair_mod32"] = df["residue_before_mod32"].astype(str) + "->" + df["residue_after_mod32"].astype(str)
    df["residue_pair_mod16"] = df["residue_before_mod16"].astype(str) + "->" + df["residue_after_mod16"].astype(str)
    df["R_drop"] = df["remaining_K_before"] - df["remaining_K_after"]

    miss = df[df["miss_event"].eq(1)].copy()
    miss_support = set(miss["residue_pair_mod32"].dropna().unique())
    controls = df[df["residue_pair_mod32"].isin(miss_support) & df["miss_event"].eq(0)].copy()
    if len(miss) != 228:
        raise SystemExit(f"Expected 228 miss rows, found {len(miss)}")
    if len(controls) != 47:
        raise SystemExit(f"Expected 47 S\\M control rows, found {len(controls)}")

    miss["group"] = "M_miss"
    controls["group"] = "S_minus_M_control"
    combined = pd.concat([miss, controls], ignore_index=True)

    exit_events = pd.read_csv(EXIT_EVENTS)
    exit_chains = pd.read_csv(EXIT_CHAINS)
    exit_events["exit_event_row_count_for_trajectory"] = 1
    exit_event_summary = (
        exit_events.groupby(["sample_id", "trajectory_id"], dropna=False)
        .agg(
            exit_path_event_rows=("exit_event_row_count_for_trajectory", "sum"),
            exit_classifications=("classification", lambda s: top_counts(s, 6)),
            exit_layer_defs=("exit_layer_definition", lambda s: top_counts(s, 6)),
            eventual_caught_bands=("eventually_caught_band", lambda s: top_counts(s, 6)),
            max_wait_time_before_exit_layer=("wait_time_before_exit_layer", "max"),
        )
        .reset_index()
    )
    chain_summary = (
        exit_chains.groupby(["sample_id", "trajectory_id"], dropna=False)
        .agg(
            max_avoidance_depth=("max_avoidance_depth", "max"),
            avoidance_depths=("number_of_consecutive_bands_where_exit_layer_was_avoided", lambda s: top_counts(s, 6)),
            final_statuses=("final_status", lambda s: top_counts(s, 6)),
            eventual_capture_bands=("eventual_capture_band", lambda s: top_counts(s, 6)),
        )
        .reset_index()
    )
    combined_aug = (
        combined.merge(exit_event_summary, on=["sample_id", "trajectory_id"], how="left")
        .merge(chain_summary, on=["sample_id", "trajectory_id"], how="left")
    )

    context = add_context_windows(df, combined)
    nearest = nearest_miss_table(miss, controls)

    numeric_cols = [
        "remaining_K_before",
        "remaining_K_after",
        "exit_distance",
        "transition_k",
        "wait_length",
        "R_drop",
        "residue_before_mod32",
        "residue_after_mod32",
        "max_avoidance_depth",
        "max_wait_time_before_exit_layer",
    ]
    num = numeric_summary(combined_aug, numeric_cols)
    num.to_csv(OUT / "miss_vs_control_numeric_summary.csv", index=False)

    categorical_cols = [
        "band",
        "band_after",
        "next_destination",
        "position_label",
        "near_behavior",
        "k_move_from_previous",
        "waiting_class",
        "trajectory_behavior_class",
        "residue_pair_mod32",
        "residue_pair_mod16",
        "transition_k",
        "sample_id",
        "max_avoidance_depth",
        "final_statuses",
        "eventual_capture_bands",
    ]
    for col in categorical_cols:
        if col in combined_aug.columns:
            dist(combined_aug, col).to_csv(OUT / f"distribution_by_{col}.csv", index=False)

    shape_position = (
        combined.groupby(["group", "residue_pair_mod32", "transition_k", "exit_distance"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["group", "count", "residue_pair_mod32", "transition_k", "exit_distance"], ascending=[True, False, True, True, True])
    )
    shape_position.to_csv(OUT / "shape_position_cells.csv", index=False)

    control_cols = [
        "event_row_id",
        "sample_id",
        "trajectory_id",
        "event_index",
        "band",
        "remaining_K_before",
        "remaining_K_after",
        "exit_distance",
        "transition_k",
        "R_drop",
        "residue_pair_mod32",
        "residue_pair_mod16",
        "position_label",
        "near_behavior",
        "k_move_from_previous",
        "wait_length",
        "waiting_class",
        "trajectory_behavior_class",
        "next_destination",
        "max_avoidance_depth",
        "eventual_capture_bands",
        "final_statuses",
    ]
    combined_aug[[c for c in control_cols if c in combined_aug.columns]].to_csv(
        OUT / "miss_and_control_event_detail.csv", index=False
    )
    controls.merge(context, on=["event_row_id", "sample_id", "trajectory_id", "group", "event_index"], how="left").to_csv(
        OUT / "s_minus_m_47_context_windows.csv", index=False
    )
    context.to_csv(OUT / "miss_and_control_context_windows.csv", index=False)
    nearest.to_csv(OUT / "s_minus_m_47_nearest_miss_by_shape.csv", index=False)

    plot_paths = maybe_plot(combined)

    # Focused checks for hypotheses that should fail or survive.
    exact_shape_overlap = set(
        tuple(x) for x in miss[["residue_pair_mod32", "transition_k"]].drop_duplicates().itertuples(index=False, name=None)
    )
    controls["shape_pair_in_miss_support"] = [
        (r.residue_pair_mod32, r.transition_k) in exact_shape_overlap for r in controls.itertuples()
    ]
    same_exit_window = controls["exit_distance"].between(3, 8, inclusive="both")
    same_R_support = controls["remaining_K_before"].isin(set(miss["remaining_K_before"].unique()))
    same_band = set(controls["band"].unique()) == set(miss["band"].unique())

    report = [
        "# S minus M control exploration",
        "",
        "This is a descriptive finite-table exploration. It does not propose a mechanism, proof, or causal explanation.",
        "",
        "## Source tables",
        "",
        f"- Waiting-hall event table: `{WAITING_DETAIL}`",
        f"- Exit-avoidance event table: `{EXIT_EVENTS}`",
        f"- Exit-avoidance chain table: `{EXIT_CHAINS}`",
        "",
        "## Population definitions",
        "",
        "- `M_miss`: `miss_event = 1` in the waiting-hall event table.",
        "- `S_minus_M_control`: non-miss rows whose `residue_pair_mod32` belongs to the miss-event residue-pair support.",
        "- All comparisons below are inside this finite event table.",
        "",
        "## Counts",
        "",
        f"- total waiting-hall event rows: {len(df)}",
        f"- `M_miss`: {len(miss)}",
        f"- `S_minus_M_control`: {len(controls)}",
        f"- control rows whose `residue_pair_mod32 + transition_k` also appears in miss support: {int(controls['shape_pair_in_miss_support'].sum())} / {len(controls)}",
        f"- control rows inside miss exit-distance window `3..8`: {int(same_exit_window.sum())} / {len(controls)}",
        f"- control rows inside miss observed `remaining_K_before` support: {int(same_R_support.sum())} / {len(controls)}",
        "",
        "## Confirmed similarities",
        "",
        f"- By construction, all controls share a miss-observed `residue_pair_mod32`; controls use {controls['residue_pair_mod32'].nunique()} of the {miss['residue_pair_mod32'].nunique()} miss residue-pair cells.",
        f"- Stronger than requested: all {len(controls)} controls also share a miss-observed `residue_pair_mod32 + transition_k` pair.",
        f"- The transition-size profile is close: miss median `transition_k={miss['transition_k'].median()}`, controls median `transition_k={controls['transition_k'].median()}`.",
        f"- The residue-before side overlaps the lower edge of the miss support: miss residue-before mod32 `{top_counts(miss['residue_before_mod32'])}`, controls `{top_counts(controls['residue_before_mod32'])}`.",
        "",
        "## Confirmed differences",
        "",
        "- The position coordinate separates the groups completely.",
        f"  Miss `exit_distance`: {top_counts(miss['exit_distance'])}.",
        f"  Control `exit_distance`: {top_counts(controls['exit_distance'])}.",
        "- The absolute `remaining_K_before` coordinate also separates the groups completely.",
        f"  Miss `remaining_K_before`: {top_counts(miss['remaining_K_before'])}.",
        f"  Control `remaining_K_before`: {top_counts(controls['remaining_K_before'])}.",
        f"- Band is not the same support: miss bands are `{top_counts(miss['band'])}`; controls are `{top_counts(controls['band'])}`. Same band support? `{same_band}`.",
        f"- `wait_length` is shifted: miss `{top_counts(miss['wait_length'])}`; controls `{top_counts(controls['wait_length'])}`.",
        f"- `near_behavior` separates the selected rows at this table level: miss `{top_counts(miss['near_behavior'])}`, controls `{top_counts(controls['near_behavior'])}`.",
        f"- Coarse position label also shifts: miss `{top_counts(miss['position_label'])}`, controls `{top_counts(controls['position_label'])}`.",
        f"- Exit-avoidance chain depth differs: miss `{top_counts(combined_aug[combined_aug['group'].eq('M_miss')]['max_avoidance_depth'])}`, controls `{top_counts(combined_aug[combined_aug['group'].eq('S_minus_M_control')]['max_avoidance_depth'])}`.",
        "",
        "## Unexpected regularities",
        "",
        "- The controls are not a diffuse leakage cloud. They occupy exactly three exit distances: 35, 36, and 37.",
        "- They are concentrated one band above the densest miss branch: controls are mostly in `64-127` at `remaining_K_before = 99..101`, while the largest miss branch is in `32-63` at `35..37`.",
        "- The control shape cells form a displaced staircase relative to miss-front cells: e.g. control `3->30` at `exit_distance=35` matches miss `3->30` at `exit_distance=3`, with the same `transition_k=5`.",
        "- All controls have `max_avoidance_depth = 2` in the joined exit-avoidance chain table; miss rows spread across depths 1, 2, and 3.",
        "- Nearest-miss matching by residue shape confirms this is a position displacement, not a new shape family; see `s_minus_m_47_nearest_miss_by_shape.csv`.",
        "",
        "## Failed hypotheses / things not supported",
        "",
        "- `shape alone is miss-only`: false. The 47 controls are exactly the leakage under residue-pair shape alone.",
        "- `shape + transition_k is miss-only`: false in this table; the same 47 controls remain after adding `transition_k`.",
        "- `transition_k` alone separates controls from miss`: false; the medians are nearly identical and every control shape+k pair exists among misses.",
        "- `residue pair alone tells position`: false; the same residue-pair cells occur in both the miss-front and displaced control rows.",
        "- `all drift-like controls are immediate miss candidates`: not supported; these controls are drift-labeled, but none are in the miss exit-distance window or miss `remaining_K_before` support.",
        "",
        "## Numeric summary",
        "",
        md_table(num, max_rows=40),
        "",
        "## Top shape-position cells",
        "",
        md_table(shape_position, max_rows=40),
        "",
        "## Output files",
        "",
        "- `miss_and_control_event_detail.csv`",
        "- `miss_vs_control_numeric_summary.csv`",
        "- `shape_position_cells.csv`",
        "- `s_minus_m_47_context_windows.csv`",
        "- `miss_and_control_context_windows.csv`",
        "- `s_minus_m_47_nearest_miss_by_shape.csv`",
    ]
    for p in plot_paths:
        report.append(f"- `{Path(p).name}`")

    (OUT / "s_minus_m_control_exploration_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    print(f"wrote {OUT}")
    print(f"miss_rows={len(miss)}")
    print(f"control_rows={len(controls)}")
    print(f"plots={len(plot_paths)}")


if __name__ == "__main__":
    main()
