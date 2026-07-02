from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Iterable

import pandas as pd


ROOT = Path(r"C:\Users\yauki\Documents\Codex\2026-07-01\new-chat")
OUT = ROOT / "outputs" / "s_minus_m_suffix_pairing"
DEPTH_DETAIL = ROOT / "outputs" / "s_minus_m_depth2_chain_exploration" / "control_miss_depth2_depth3_event_chain_detail.csv"
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
STAGE_BANDS = ["32-63", "16-31", "8-15", "4-7"]


def as_int(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype("Int64")


def top_counts(values: Iterable[object], n: int = 8) -> str:
    c = Counter("NA" if pd.isna(v) or v == "" else str(v) for v in values)
    return "; ".join(f"{k}:{v}" for k, v in c.most_common(n))


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


def parse_pattern(pattern: object) -> dict[str, str]:
    out: dict[str, str] = {}
    if pd.isna(pattern):
        return out
    for item in str(pattern).split(">"):
        if ":" not in item:
            continue
        band, status = item.split(":", 1)
        out[band.strip()] = status.strip()
    return out


def classify_stage(row: pd.Series, band: str) -> str:
    status = row.get(f"{band}_chain_status", "")
    run_bands = set(str(row.get("lower5_run_bands", "")).split(">"))
    if status == "" or pd.isna(status):
        return "absent"
    if band in run_bands and status == "avoid":
        return "avoid_in_max_depth_run"
    if status == "avoid":
        return "avoid_not_in_max_depth_run"
    if status in {"caught", "avoid_then_caught"}:
        return status
    return "other"


def residue_pair(before: object, after: object) -> str:
    if pd.isna(before) or pd.isna(after):
        return ""
    return f"{int(before) % 32}->{int(after) % 32}"


def load_waiting() -> pd.DataFrame:
    df = pd.read_csv(WAITING_DETAIL)
    df = df.copy()
    for col in ["event_index", "remaining_K_before", "remaining_K_after", "transition_k", "distance_from_exit", "wait_length"]:
        df[col] = as_int(df[col])
    df["residue_pair_mod32"] = df.apply(lambda r: residue_pair(r["remaining_K_before"], r["remaining_K_after"]), axis=1)
    return df


def build_stage_table(waiting: pd.DataFrame, exit_events: pd.DataFrame, chains: pd.DataFrame) -> pd.DataFrame:
    lower_events = exit_events[exit_events["exit_layer_id"].eq("lower_5pct")].copy()
    max_chain = chains[chains["exit_layer_id"].eq("lower_5pct")].copy()
    max_chain = max_chain[
        [
            "sample_id",
            "trajectory_id",
            "number_of_consecutive_bands_where_exit_layer_was_avoided",
            "max_avoidance_depth",
            "avoidance_pattern_by_band",
            "avoidance_runs_by_band",
            "eventual_capture_band",
            "final_status",
        ]
    ].rename(
        columns={
            "number_of_consecutive_bands_where_exit_layer_was_avoided": "lower5_run_length",
            "max_avoidance_depth": "lower5_max_depth",
            "avoidance_pattern_by_band": "lower5_pattern",
            "avoidance_runs_by_band": "lower5_run_bands",
            "eventual_capture_band": "lower5_capture_band",
            "final_status": "lower5_final_status",
        }
    )

    base_keys = max_chain[["sample_id", "trajectory_id"]].drop_duplicates()
    records = []
    grouped_wait = {
        key: g.sort_values("event_index").reset_index(drop=True)
        for key, g in waiting.groupby(["sample_id", "trajectory_id", "band"], dropna=False)
    }
    grouped_exit = {
        key: g.reset_index(drop=True)
        for key, g in lower_events.groupby(["sample_id", "trajectory_id", "band"], dropna=False)
    }
    for _, keyrow in base_keys.iterrows():
        rec = {"sample_id": keyrow["sample_id"], "trajectory_id": keyrow["trajectory_id"]}
        for band in STAGE_BANDS:
            wg = grouped_wait.get((keyrow["sample_id"], keyrow["trajectory_id"], band))
            eg = grouped_exit.get((keyrow["sample_id"], keyrow["trajectory_id"], band))
            prefix = band
            if wg is not None and not wg.empty:
                first = wg.iloc[0]
                last = wg.iloc[-1]
                rec[f"{prefix}_entry_R"] = first["remaining_K_before"]
                rec[f"{prefix}_entry_k"] = first["transition_k"]
                rec[f"{prefix}_entry_residue_pair_mod32"] = first["residue_pair_mod32"]
                rec[f"{prefix}_exit_R"] = last["remaining_K_after"]
                rec[f"{prefix}_exit_k"] = last["transition_k"]
                rec[f"{prefix}_exit_residue_pair_mod32"] = last["residue_pair_mod32"]
                rec[f"{prefix}_wait_length"] = first["wait_length"]
                rec[f"{prefix}_near_behavior"] = top_counts(wg["near_behavior"], 5)
                rec[f"{prefix}_position_label"] = top_counts(wg["position_label"], 5)
                rec[f"{prefix}_R_sequence"] = ",".join(str(x) for x in wg["remaining_K_before"].tolist()[:20])
                rec[f"{prefix}_k_sequence_waiting"] = ",".join(str(x) for x in wg["transition_k"].tolist()[:20])
            else:
                for suffix in [
                    "entry_R",
                    "entry_k",
                    "entry_residue_pair_mod32",
                    "exit_R",
                    "exit_k",
                    "exit_residue_pair_mod32",
                    "wait_length",
                    "near_behavior",
                    "position_label",
                    "R_sequence",
                    "k_sequence_waiting",
                ]:
                    rec[f"{prefix}_{suffix}"] = ""
            if eg is not None and not eg.empty:
                erow = eg.iloc[0]
                rec[f"{prefix}_classification"] = erow["classification"]
                rec[f"{prefix}_avoided_exit_layer_in_window"] = erow["avoided_exit_layer_in_window"]
                rec[f"{prefix}_eventually_caught_band"] = erow["eventually_caught_band"]
                rec[f"{prefix}_exit_event_k_sequence"] = erow["k_sequence_until_resolution"]
                rec[f"{prefix}_max_R_in_band"] = erow["max_remaining_K_in_band"]
                rec[f"{prefix}_min_R_in_band"] = erow["min_remaining_K_in_band"]
                k_seq = [x.strip() for x in str(erow["k_sequence_until_resolution"]).split(",") if x.strip()]
                first_k = k_seq[0] if k_seq else ""
                last_k = k_seq[-1] if k_seq else ""
                before_mod32 = erow["residue_before_avoidance_mod32"]
                try:
                    after_mod32 = (int(before_mod32) - int(first_k)) % 32 if first_k != "" else ""
                except Exception:
                    after_mod32 = ""
                rec[f"{prefix}_exit_event_entry_R"] = erow["max_remaining_K_in_band"]
                rec[f"{prefix}_exit_event_exit_R"] = erow["min_remaining_K_in_band"]
                rec[f"{prefix}_exit_event_entry_k"] = first_k
                rec[f"{prefix}_exit_event_last_k"] = last_k
                rec[f"{prefix}_exit_event_entry_residue_pair_mod32"] = (
                    f"{before_mod32}->{after_mod32}" if after_mod32 != "" else ""
                )
            else:
                for suffix in [
                    "classification",
                    "avoided_exit_layer_in_window",
                    "eventually_caught_band",
                    "exit_event_k_sequence",
                    "max_R_in_band",
                    "min_R_in_band",
                    "exit_event_entry_R",
                    "exit_event_exit_R",
                    "exit_event_entry_k",
                    "exit_event_last_k",
                    "exit_event_entry_residue_pair_mod32",
                ]:
                    rec[f"{prefix}_{suffix}"] = ""
        records.append(rec)

    stage = pd.DataFrame(records).merge(max_chain, on=["sample_id", "trajectory_id"], how="left")
    statuses = stage["lower5_pattern"].apply(parse_pattern)
    for band in STAGE_BANDS:
        stage[f"{band}_chain_status"] = statuses.apply(lambda d: d.get(band, ""))
        stage[f"{band}_stage_class"] = stage.apply(lambda r: classify_stage(r, band), axis=1)
        # Use exit-event descriptors as fallback for lower bands not present in the waiting-hall row window.
        for target, fallback in [
            ("entry_R", "exit_event_entry_R"),
            ("exit_R", "exit_event_exit_R"),
            ("entry_k", "exit_event_entry_k"),
            ("exit_k", "exit_event_last_k"),
            ("entry_residue_pair_mod32", "exit_event_entry_residue_pair_mod32"),
        ]:
            col = f"{band}_{target}"
            fb = f"{band}_{fallback}"
            if col in stage.columns and fb in stage.columns:
                stage[col] = stage[col].where(stage[col].astype(str).ne(""), stage[fb])
    return stage


def pick_nearest(control: pd.Series, miss_pool: pd.DataFrame) -> pd.Series:
    scored = miss_pool.copy()
    score = pd.Series(0, index=scored.index, dtype=float)
    # Prefer the same suffix stages first.
    for band in ["16-31", "8-15", "4-7"]:
        score += (scored[f"{band}_chain_status"].astype(str) != str(control[f"{band}_chain_status"])) * 10
        score += (scored[f"{band}_entry_residue_pair_mod32"].astype(str) != str(control[f"{band}_entry_residue_pair_mod32"])) * 3
        score += (scored[f"{band}_entry_k"].astype(str) != str(control[f"{band}_entry_k"])) * 2
        c_val = pd.to_numeric(pd.Series([control[f"{band}_entry_R"]]), errors="coerce").iloc[0]
        m_val = pd.to_numeric(scored[f"{band}_entry_R"], errors="coerce")
        score += (m_val - c_val).abs().fillna(99) / 100
    # Then prefer same selected local shape.
    score += (scored["selected_residue_pair_mod32"].astype(str) != str(control["selected_residue_pair_mod32"])) * 2
    score += (scored["selected_transition_k"].astype(str) != str(control["selected_transition_k"])) * 1
    scored["pair_score"] = score
    return scored.sort_values(["pair_score", "sample_id", "trajectory_id"]).iloc[0]


def constants(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    rows = []
    for col in cols:
        counts = df[col].fillna("NA").astype(str).value_counts()
        if counts.empty:
            continue
        rows.append(
            {
                "feature": col,
                "unique_values": int(counts.size),
                "top_value": counts.index[0],
                "top_count": int(counts.iloc[0]),
                "exceptions": int(len(df) - counts.iloc[0]),
                "distribution": "; ".join(f"{k}:{v}" for k, v in counts.items()),
            }
        )
    return pd.DataFrame(rows).sort_values(["exceptions", "unique_values", "feature"])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    detail = pd.read_csv(DEPTH_DETAIL)
    waiting = load_waiting()
    exit_events = pd.read_csv(EXIT_EVENTS)
    chains = pd.read_csv(EXIT_CHAINS)
    for frame in [detail, waiting, exit_events, chains]:
        if "trajectory_id" in frame.columns:
            frame["trajectory_id"] = as_int(frame["trajectory_id"])

    stage = build_stage_table(waiting, exit_events, chains)
    selected = detail[
        detail["comparison_group"].isin(["S_minus_M_control_depth2", "M_miss_depth3"])
    ].copy()
    selected = selected.rename(
        columns={
            "remaining_K_before": "selected_R_before",
            "remaining_K_after": "selected_R_after",
            "transition_k": "selected_transition_k",
            "residue_pair_mod32": "selected_residue_pair_mod32",
            "band": "selected_band",
            "event_index": "selected_event_index",
            "near_behavior": "selected_near_behavior",
        }
    )
    selected_cols = [
        "sample_id",
        "trajectory_id",
        "event_row_id",
        "comparison_group",
        "selected_band",
        "selected_event_index",
        "selected_R_before",
        "selected_R_after",
        "selected_transition_k",
        "selected_residue_pair_mod32",
        "selected_near_behavior",
        "exit_distance",
        "wait_length",
        "trajectory_behavior_class",
    ]
    merged = selected[selected_cols].merge(stage, on=["sample_id", "trajectory_id"], how="left")
    merged.to_csv(OUT / "chain_stage_comparison_table.csv", index=False)

    controls = merged[merged["comparison_group"].eq("S_minus_M_control_depth2")].copy()
    miss3 = merged[merged["comparison_group"].eq("M_miss_depth3")].copy()

    # Classify 32-63 stage explicitly.
    stage32 = (
        merged.groupby(["comparison_group", "32-63_stage_class", "32-63_chain_status", "32-63_classification"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["comparison_group", "count"], ascending=[True, False])
    )
    stage32.to_csv(OUT / "stage_32_63_classification.csv", index=False)

    suffix_cols = []
    for band in ["16-31", "8-15", "4-7"]:
        suffix_cols.extend(
            [
                f"{band}_stage_class",
                f"{band}_chain_status",
                f"{band}_classification",
                f"{band}_entry_R",
                f"{band}_entry_k",
                f"{band}_entry_residue_pair_mod32",
                f"{band}_exit_R",
                f"{band}_exit_k",
                f"{band}_exit_residue_pair_mod32",
                f"{band}_eventually_caught_band",
                f"{band}_exit_event_k_sequence",
            ]
        )
    suffix_summary = (
        merged.groupby(["comparison_group"] + [f"{band}_stage_class" for band in ["16-31", "8-15", "4-7"]], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["comparison_group", "count"], ascending=[True, False])
    )
    suffix_summary.to_csv(OUT / "suffix_stage_class_summary.csv", index=False)

    pair_rows = []
    for _, control in controls.iterrows():
        nearest = pick_nearest(control, miss3)
        row = {
            "control_event_row_id": control["event_row_id"],
            "control_sample_id": control["sample_id"],
            "control_trajectory_id": control["trajectory_id"],
            "control_selected_shape": f"{control['selected_residue_pair_mod32']}|k={control['selected_transition_k']}",
            "control_32_63_stage_class": control["32-63_stage_class"],
            "control_32_63_status": control["32-63_chain_status"],
            "control_suffix_classes": ">".join(str(control[f"{b}_stage_class"]) for b in ["16-31", "8-15", "4-7"]),
            "control_suffix_entry_shapes": ">".join(
                f"{b}:{control[f'{b}_entry_residue_pair_mod32']}|k={control[f'{b}_entry_k']}"
                for b in ["16-31", "8-15", "4-7"]
            ),
            "matched_miss_event_row_id": nearest["event_row_id"],
            "matched_miss_sample_id": nearest["sample_id"],
            "matched_miss_trajectory_id": nearest["trajectory_id"],
            "matched_miss_selected_shape": f"{nearest['selected_residue_pair_mod32']}|k={nearest['selected_transition_k']}",
            "matched_miss_32_63_stage_class": nearest["32-63_stage_class"],
            "matched_miss_32_63_status": nearest["32-63_chain_status"],
            "matched_miss_suffix_classes": ">".join(str(nearest[f"{b}_stage_class"]) for b in ["16-31", "8-15", "4-7"]),
            "matched_miss_suffix_entry_shapes": ">".join(
                f"{b}:{nearest[f'{b}_entry_residue_pair_mod32']}|k={nearest[f'{b}_entry_k']}"
                for b in ["16-31", "8-15", "4-7"]
            ),
            "pair_score": nearest["pair_score"],
            "same_selected_shape": (
                control["selected_residue_pair_mod32"] == nearest["selected_residue_pair_mod32"]
                and str(control["selected_transition_k"]) == str(nearest["selected_transition_k"])
            ),
            "same_16_31_entry_shape": (
                control["16-31_entry_residue_pair_mod32"] == nearest["16-31_entry_residue_pair_mod32"]
                and str(control["16-31_entry_k"]) == str(nearest["16-31_entry_k"])
            ),
            "same_8_15_entry_shape": (
                control["8-15_entry_residue_pair_mod32"] == nearest["8-15_entry_residue_pair_mod32"]
                and str(control["8-15_entry_k"]) == str(nearest["8-15_entry_k"])
            ),
            "same_4_7_entry_shape": (
                control["4-7_entry_residue_pair_mod32"] == nearest["4-7_entry_residue_pair_mod32"]
                and str(control["4-7_entry_k"]) == str(nearest["4-7_entry_k"])
            ),
        }
        pair_rows.append(row)
    pairs = pd.DataFrame(pair_rows).sort_values(["pair_score", "control_sample_id", "control_trajectory_id"])
    pairs.to_csv(OUT / "per_control_paired_card_table.csv", index=False)

    pair_cards = ["# Per-control paired cards", ""]
    for i, row in enumerate(pairs.itertuples(), start=1):
        pair_cards.extend(
            [
                f"## Pair {i}: control {row.control_sample_id}/{row.control_trajectory_id} -> miss {row.matched_miss_sample_id}/{row.matched_miss_trajectory_id}",
                "",
                f"- selected shape: control `{row.control_selected_shape}`, miss `{row.matched_miss_selected_shape}`, same `{row.same_selected_shape}`",
                f"- 32-63: control `{row.control_32_63_stage_class}` / `{row.control_32_63_status}`, miss `{row.matched_miss_32_63_stage_class}` / `{row.matched_miss_32_63_status}`",
                f"- suffix classes: control `{row.control_suffix_classes}`, miss `{row.matched_miss_suffix_classes}`",
                f"- suffix entry shapes: control `{row.control_suffix_entry_shapes}`, miss `{row.matched_miss_suffix_entry_shapes}`",
                f"- same suffix entry shapes: 16-31 `{row.same_16_31_entry_shape}`, 8-15 `{row.same_8_15_entry_shape}`, 4-7 `{row.same_4_7_entry_shape}`",
                f"- pairing score: `{row.pair_score}`",
                "",
            ]
        )
    (OUT / "per_control_paired_cards.md").write_text("\n".join(pair_cards), encoding="utf-8")

    inv_cols = [
        "32-63_stage_class",
        "32-63_chain_status",
        "32-63_classification",
        "16-31_stage_class",
        "16-31_chain_status",
        "16-31_classification",
        "8-15_stage_class",
        "8-15_chain_status",
        "8-15_classification",
        "4-7_stage_class",
        "4-7_chain_status",
        "4-7_classification",
        "lower5_capture_band",
        "lower5_final_status",
        "selected_near_behavior",
        "trajectory_behavior_class",
    ]
    control_inv = constants(controls, inv_cols)
    miss3_inv = constants(miss3, inv_cols)
    control_inv.to_csv(OUT / "control_invariants_and_near_invariants.csv", index=False)
    miss3_inv.to_csv(OUT / "miss_depth3_invariants_and_near_invariants.csv", index=False)

    cluster_cols = [
        "32-63_stage_class",
        "16-31_stage_class",
        "8-15_stage_class",
        "4-7_stage_class",
        "trajectory_behavior_class",
        "selected_band",
    ]
    clusters = (
        controls.groupby(cluster_cols, dropna=False)
        .size()
        .reset_index(name="control_count")
        .sort_values(["control_count"] + cluster_cols, ascending=[False] + [True] * len(cluster_cols))
    )
    clusters.to_csv(OUT / "control_clusters.csv", index=False)

    same_suffix_stage_classes = (
        controls[["16-31_stage_class", "8-15_stage_class", "4-7_stage_class"]]
        .drop_duplicates()
        .merge(
            miss3[["16-31_stage_class", "8-15_stage_class", "4-7_stage_class"]].drop_duplicates(),
            on=["16-31_stage_class", "8-15_stage_class", "4-7_stage_class"],
            how="inner",
        )
    )

    report = [
        "# Paired suffix comparison: controls vs miss-depth-3",
        "",
        "Finite-sample descriptive exploration only. No mechanism, proof, causality, or global Collatz claim is made.",
        "",
        "## Populations",
        "",
        f"- Controls: {len(controls)}",
        f"- Miss-depth-3 rows: {len(miss3)}",
        "",
        "## Suffix Hypothesis Check",
        "",
        "Hypothesis under stress test: controls are suffix-only analogues of miss-depth-3 chains; they contain the `16-31 > 8-15 -> 4-7` suffix but lack the `32-63` avoidance prefix.",
        "",
        "Result:",
        "",
        f"- Shared suffix stage-class patterns between controls and miss-depth-3: {len(same_suffix_stage_classes)} unique pattern(s).",
        f"- Control 32-63 classification: `{top_counts(controls['32-63_stage_class'])}`.",
        f"- Miss-depth-3 32-63 classification: `{top_counts(miss3['32-63_stage_class'])}`.",
        f"- Control suffix classes: `{top_counts(controls['16-31_stage_class'] + '>' + controls['8-15_stage_class'] + '>' + controls['4-7_stage_class'])}`.",
        f"- Miss-depth-3 suffix classes: `{top_counts(miss3['16-31_stage_class'] + '>' + miss3['8-15_stage_class'] + '>' + miss3['4-7_stage_class'])}`.",
        "",
        "## Main Read",
        "",
        "- The suffix hypothesis is supported at the coarse chain-status level: controls and miss-depth-3 share the `16-31:avoid > 8-15:avoid` suffix and then reach the `4-7` capture layer.",
        "- The 32-63 stage is the clean structural split: controls have `32-63:avoid_then_caught`, while miss-depth-3 has `32-63:avoid_in_max_depth_run`.",
        "- Therefore controls are not missing the 32-63 band as an absent stage; they usually have a 32-63 event, but it is already `avoid_then_caught`, so it is not counted as part of the consecutive max-depth avoidance run.",
        "- At finer local-shape level, suffix similarity is weaker than coarse suffix similarity. Pairing by 16-31/8-15/4-7 entry shapes rarely makes every suffix stage identical.",
        "",
        "## 32-63 Stage Classification",
        "",
        md_table(stage32),
        "",
        "## Suffix Stage Summary",
        "",
        md_table(suffix_summary),
        "",
        "## Control Clusters",
        "",
        md_table(clusters),
        "",
        "## Pairing Quality",
        "",
        f"- Same selected shape in nearest-pair table: {int(pairs['same_selected_shape'].sum())} / {len(pairs)}",
        f"- Same 16-31 entry shape: {int(pairs['same_16_31_entry_shape'].sum())} / {len(pairs)}",
        f"- Same 8-15 entry shape: {int(pairs['same_8_15_entry_shape'].sum())} / {len(pairs)}",
        f"- Same 4-7 entry shape: {int(pairs['same_4_7_entry_shape'].sum())} / {len(pairs)}",
        "",
        "## Failed Hypotheses",
        "",
        "- `Controls lack a 32-63 stage entirely`: false. The stage is present, but classified differently.",
        "- `The only difference is absence of 32-63`: false as phrased; the difference is 32-63 status, not absence.",
        "- `Suffixes are exactly identical at all local descriptors`: not supported. The coarse chain suffix matches better than the local entry-shape descriptors.",
        "- `Controls are depth-2 miss analogues`: still not supported; they are better described as suffix-level analogues with a different 32-63 prefix status.",
        "",
        "## Invariants / Near-Invariants",
        "",
        "### Controls",
        "",
        md_table(control_inv, max_rows=40),
        "",
        "### Miss-depth-3",
        "",
        md_table(miss3_inv, max_rows=40),
        "",
        "## Suggested Next Exploration",
        "",
        "- Drill into the `32-63:avoid_then_caught` vs `32-63:avoid` split using the 32-63 stage rows only.",
        "- Compare the last 32-63 event before entering 16-31: is the capture/avoid distinction visible in `entry_R`, `exit_R`, or k-sequence?",
        "- Keep control subclusters split by `drift_down` vs `mid_band_wait_then_drop`; they share the suffix class but may differ upstream.",
        "",
        "## Output Files",
        "",
        "- `chain_stage_comparison_table.csv`",
        "- `stage_32_63_classification.csv`",
        "- `suffix_stage_class_summary.csv`",
        "- `per_control_paired_card_table.csv`",
        "- `per_control_paired_cards.md`",
        "- `control_clusters.csv`",
        "- `control_invariants_and_near_invariants.csv`",
        "- `miss_depth3_invariants_and_near_invariants.csv`",
    ]
    (OUT / "paired_suffix_comparison_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"controls={len(controls)} miss_depth3={len(miss3)} pairs={len(pairs)}")
    print(f"same_suffix_patterns={len(same_suffix_stage_classes)}")


if __name__ == "__main__":
    main()
