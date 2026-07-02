from __future__ import annotations

from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Iterable

import pandas as pd


ROOT = Path(r"C:\Users\yauki\Documents\Codex\2026-07-01\new-chat")
SOURCE = ROOT / "outputs" / "s_minus_m_suffix_pairing" / "chain_stage_comparison_table.csv"
PAIR_SOURCE = ROOT / "outputs" / "s_minus_m_suffix_pairing" / "per_control_paired_card_table.csv"
OUT = ROOT / "outputs" / "status_split_32_63_audit"


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


def seq_list(value: object) -> list[str]:
    if pd.isna(value) or str(value).strip() == "":
        return []
    return [x.strip() for x in str(value).split(",") if x.strip()]


def first_n(value: object, n: int = 5) -> str:
    return ",".join(seq_list(value)[:n])


def last_n(value: object, n: int = 5) -> str:
    xs = seq_list(value)
    return ",".join(xs[-n:])


def count_seq(value: object) -> int:
    return len(seq_list(value))


def as_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def build_stage(df: pd.DataFrame) -> pd.DataFrame:
    rows = df[df["comparison_group"].isin(["S_minus_M_control_depth2", "M_miss_depth3"])].copy()
    rows["group"] = rows["comparison_group"].map(
        {
            "S_minus_M_control_depth2": "control_32_63_avoid_then_caught",
            "M_miss_depth3": "miss_depth3_32_63_avoid",
        }
    )
    out = pd.DataFrame(
        {
            "group": rows["group"],
            "sample_id": rows["sample_id"],
            "trajectory_id": rows["trajectory_id"],
            "event_row_id": rows["event_row_id"],
            "selected_band": rows["selected_band"],
            "selected_shape": rows["selected_residue_pair_mod32"].astype(str) + "|k=" + rows["selected_transition_k"].astype(str),
            "selected_near_behavior": rows["selected_near_behavior"],
            "trajectory_behavior_class": rows["trajectory_behavior_class"],
            "stage_chain_status": rows["32-63_chain_status"],
            "stage_class": rows["32-63_stage_class"],
            "stage_event_classification": rows["32-63_classification"],
            "stage_avoided_exit_layer_in_window": rows["32-63_avoided_exit_layer_in_window"],
            "stage_eventually_caught_band": rows["32-63_eventually_caught_band"],
            "entry_R": rows["32-63_entry_R"],
            "exit_R": rows["32-63_exit_R"],
            "entry_k": rows["32-63_entry_k"],
            "exit_k": rows["32-63_exit_k"],
            "entry_residue_pair_mod32": rows["32-63_entry_residue_pair_mod32"],
            "exit_residue_pair_mod32": rows["32-63_exit_residue_pair_mod32"],
            "wait_length_inside_32_63": rows["32-63_wait_length"],
            "near_behavior_inside_32_63": rows["32-63_near_behavior"],
            "position_labels_inside_32_63": rows["32-63_position_label"],
            "R_sequence_32_63": rows["32-63_R_sequence"],
            "k_sequence_waiting_32_63": rows["32-63_k_sequence_waiting"],
            "exit_event_k_sequence_32_63": rows["32-63_exit_event_k_sequence"],
            "max_R_in_band": rows["32-63_max_R_in_band"],
            "min_R_in_band": rows["32-63_min_R_in_band"],
            "event_entry_R": rows["32-63_exit_event_entry_R"],
            "event_exit_R": rows["32-63_exit_event_exit_R"],
            "event_entry_k": rows["32-63_exit_event_entry_k"],
            "event_last_k": rows["32-63_exit_event_last_k"],
            "event_entry_residue_pair_mod32": rows["32-63_exit_event_entry_residue_pair_mod32"],
            "next_16_31_entry_R": rows["16-31_entry_R"],
            "next_16_31_entry_k": rows["16-31_entry_k"],
            "next_16_31_entry_residue_pair_mod32": rows["16-31_entry_residue_pair_mod32"],
            "next_16_31_stage_class": rows["16-31_stage_class"],
            "next_16_31_chain_status": rows["16-31_chain_status"],
            "lower5_run_bands": rows["lower5_run_bands"],
            "lower5_capture_band": rows["lower5_capture_band"],
            "lower5_final_status": rows["lower5_final_status"],
        }
    )
    out["entry_R"] = as_num(out["entry_R"])
    out["exit_R"] = as_num(out["exit_R"])
    out["entry_k"] = as_num(out["entry_k"])
    out["exit_k"] = as_num(out["exit_k"])
    out["wait_length_inside_32_63"] = as_num(out["wait_length_inside_32_63"])
    out["max_R_in_band"] = as_num(out["max_R_in_band"])
    out["min_R_in_band"] = as_num(out["min_R_in_band"])
    out["stage_R_drop_entry_to_exit"] = out["entry_R"] - out["exit_R"]
    out["entry_exit_distance"] = out["entry_R"] - 32
    out["last_before_R"] = as_num(out["min_R_in_band"])
    out["last_before_k"] = as_num(out["event_last_k"])
    out["last_after_R"] = out["last_before_R"] - out["last_before_k"]
    out["last_before_exit_distance"] = out["last_before_R"] - 32
    out["last_before_residue_pair_mod32"] = (
        (out["last_before_R"] % 32).astype("Int64").astype(str)
        + "->"
        + (out["last_after_R"] % 32).astype("Int64").astype(str)
    )
    out["events_inside_32_63_waiting_rows"] = out["k_sequence_waiting_32_63"].apply(count_seq)
    out["events_in_32_63_exit_event_sequence"] = out["exit_event_k_sequence_32_63"].apply(count_seq)
    out["entry_k_window_5"] = out["k_sequence_waiting_32_63"].apply(lambda x: first_n(x, 5))
    out["last_k_window_5_before_16_31"] = out["k_sequence_waiting_32_63"].apply(lambda x: last_n(x, 5))
    out["exit_event_entry_k_window_5"] = out["exit_event_k_sequence_32_63"].apply(lambda x: first_n(x, 5))
    out["exit_event_last_k_window_5"] = out["exit_event_k_sequence_32_63"].apply(lambda x: last_n(x, 5))
    out["last_event_before_16_31"] = (
        "R="
        + out["last_before_R"].fillna("").astype(str)
        + "->"
        + out["last_after_R"].fillna("").astype(str)
        + "|k="
        + out["last_before_k"].fillna("").astype(str)
        + "|res="
        + out["last_before_residue_pair_mod32"].fillna("").astype(str)
    )
    out["first_event_in_16_31"] = (
        "R="
        + out["next_16_31_entry_R"].fillna("").astype(str)
        + "|k="
        + out["next_16_31_entry_k"].fillna("").astype(str)
        + "|res="
        + out["next_16_31_entry_residue_pair_mod32"].fillna("").astype(str)
    )
    return out


def numeric_summary(stage: pd.DataFrame) -> pd.DataFrame:
    features = [
        "entry_R",
        "exit_R",
        "entry_k",
        "exit_k",
        "entry_exit_distance",
        "last_before_R",
        "last_after_R",
        "last_before_k",
        "last_before_exit_distance",
        "wait_length_inside_32_63",
        "stage_R_drop_entry_to_exit",
        "events_inside_32_63_waiting_rows",
        "events_in_32_63_exit_event_sequence",
        "max_R_in_band",
        "min_R_in_band",
    ]
    rows = []
    for group, g in stage.groupby("group"):
        for feature in features:
            s = as_num(g[feature]).dropna()
            rows.append(
                {
                    "group": group,
                    "feature": feature,
                    "n": int(s.size),
                    "min": "" if s.empty else float(s.min()),
                    "median": "" if s.empty else float(s.median()),
                    "mean": "" if s.empty else round(float(s.mean()), 6),
                    "max": "" if s.empty else float(s.max()),
                    "unique": int(s.nunique()),
                }
            )
    return pd.DataFrame(rows)


def distributions(stage: pd.DataFrame) -> pd.DataFrame:
    features = [
        "stage_chain_status",
        "stage_class",
        "stage_event_classification",
        "stage_avoided_exit_layer_in_window",
        "stage_eventually_caught_band",
        "entry_residue_pair_mod32",
        "exit_residue_pair_mod32",
        "last_before_residue_pair_mod32",
        "entry_k",
        "exit_k",
        "entry_k_window_5",
        "last_k_window_5_before_16_31",
        "exit_event_entry_k_window_5",
        "exit_event_last_k_window_5",
        "last_event_before_16_31",
        "first_event_in_16_31",
        "next_16_31_stage_class",
        "lower5_capture_band",
        "lower5_final_status",
    ]
    frames = []
    for feature in features:
        tmp = (
            stage.groupby(["group", feature], dropna=False)
            .size()
            .reset_index(name="count")
            .rename(columns={feature: "value"})
        )
        tmp.insert(1, "feature", feature)
        frames.append(tmp)
    out = pd.concat(frames, ignore_index=True)
    return out.sort_values(["feature", "group", "count", "value"], ascending=[True, True, False, True])


def invariants(stage: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "stage_chain_status",
        "stage_class",
        "stage_event_classification",
        "stage_avoided_exit_layer_in_window",
        "stage_eventually_caught_band",
        "entry_R",
        "exit_R",
        "entry_k",
        "exit_k",
        "entry_exit_distance",
        "last_before_exit_distance",
        "entry_residue_pair_mod32",
        "exit_residue_pair_mod32",
        "last_before_residue_pair_mod32",
        "wait_length_inside_32_63",
        "events_inside_32_63_waiting_rows",
        "events_in_32_63_exit_event_sequence",
        "entry_k_window_5",
        "last_k_window_5_before_16_31",
        "last_event_before_16_31",
        "first_event_in_16_31",
        "next_16_31_stage_class",
        "lower5_capture_band",
        "lower5_final_status",
    ]
    rows = []
    for group, g in stage.groupby("group"):
        for col in cols:
            counts = g[col].fillna("NA").astype(str).value_counts()
            rows.append(
                {
                    "group": group,
                    "feature": col,
                    "unique_values": int(counts.size),
                    "top_value": counts.index[0] if not counts.empty else "",
                    "top_count": int(counts.iloc[0]) if not counts.empty else 0,
                    "exceptions": int(len(g) - counts.iloc[0]) if not counts.empty else len(g),
                    "distribution": "; ".join(f"{k}:{v}" for k, v in counts.items()),
                }
            )
    return pd.DataFrame(rows).sort_values(["group", "exceptions", "unique_values", "feature"])


def minimal_selector(stage: pd.DataFrame) -> pd.DataFrame:
    candidates = [
        "stage_chain_status",
        "stage_event_classification",
        "stage_avoided_exit_layer_in_window",
        "entry_R",
        "exit_R",
        "entry_k",
        "exit_k",
        "entry_exit_distance",
        "last_before_exit_distance",
        "entry_residue_pair_mod32",
        "exit_residue_pair_mod32",
        "last_before_residue_pair_mod32",
        "wait_length_inside_32_63",
        "events_inside_32_63_waiting_rows",
        "events_in_32_63_exit_event_sequence",
        "entry_k_window_5",
        "last_k_window_5_before_16_31",
        "last_event_before_16_31",
        "first_event_in_16_31",
    ]
    rows = []
    for r in range(1, 4):
        for combo in combinations(candidates, r):
            table = stage.groupby(list(combo), dropna=False)["group"].nunique().reset_index(name="group_count")
            mixed_cells = table[table["group_count"].gt(1)]
            grouped = stage.groupby(list(combo) + ["group"], dropna=False).size().reset_index(name="count")
            # A selector separates if every coordinate tuple belongs to one group only.
            separates = mixed_cells.empty
            rows.append(
                {
                    "selector": " + ".join(combo),
                    "dimension": r,
                    "separates_groups": bool(separates),
                    "mixed_coordinate_cells": int(len(mixed_cells)),
                    "coordinate_cells": int(len(table)),
                    "top_cells": " | ".join(
                        ",".join(str(row[c]) for c in combo) + f" => {row['group']}:{row['count']}"
                        for _, row in grouped.sort_values("count", ascending=False).head(8).iterrows()
                    ),
                }
            )
    out = pd.DataFrame(rows).sort_values(["separates_groups", "dimension", "mixed_coordinate_cells", "coordinate_cells"], ascending=[False, True, True, True])
    return out


def paired_examples(stage: pd.DataFrame) -> pd.DataFrame:
    controls = stage[stage["group"].eq("control_32_63_avoid_then_caught")].copy()
    miss = stage[stage["group"].eq("miss_depth3_32_63_avoid")].copy()
    rows = []
    for _, c in controls.iterrows():
        m = miss.copy()
        score = pd.Series(0.0, index=m.index)
        for col, weight in [
            ("entry_k_window_5", 10),
            ("last_k_window_5_before_16_31", 8),
            ("entry_residue_pair_mod32", 5),
            ("exit_residue_pair_mod32", 5),
            ("first_event_in_16_31", 4),
            ("entry_k", 2),
            ("exit_k", 2),
        ]:
            score += (m[col].astype(str) != str(c[col])) * weight
        score += (as_num(m["entry_R"]) - float(c["entry_R"])).abs().fillna(999) / 100
        m["pair_score_32_63"] = score
        best = m.sort_values(["pair_score_32_63", "sample_id", "trajectory_id"]).iloc[0]
        rows.append(
            {
                "control_sample_id": c["sample_id"],
                "control_trajectory_id": c["trajectory_id"],
                "control_stage_status": c["stage_chain_status"],
                "control_entry_R": c["entry_R"],
                "control_exit_R": c["exit_R"],
                "control_entry_shape": f"{c['entry_residue_pair_mod32']}|k={c['entry_k']}",
                "control_last_event_before_16_31": c["last_event_before_16_31"],
                "control_entry_k_window_5": c["entry_k_window_5"],
                "control_last_k_window_5": c["last_k_window_5_before_16_31"],
                "miss_sample_id": best["sample_id"],
                "miss_trajectory_id": best["trajectory_id"],
                "miss_stage_status": best["stage_chain_status"],
                "miss_entry_R": best["entry_R"],
                "miss_exit_R": best["exit_R"],
                "miss_entry_shape": f"{best['entry_residue_pair_mod32']}|k={best['entry_k']}",
                "miss_last_event_before_16_31": best["last_event_before_16_31"],
                "miss_entry_k_window_5": best["entry_k_window_5"],
                "miss_last_k_window_5": best["last_k_window_5_before_16_31"],
                "pair_score_32_63": best["pair_score_32_63"],
                "same_entry_shape": c["entry_residue_pair_mod32"] == best["entry_residue_pair_mod32"]
                and str(c["entry_k"]) == str(best["entry_k"]),
                "same_last_event_before_16_31": c["last_event_before_16_31"] == best["last_event_before_16_31"],
                "same_entry_k_window_5": c["entry_k_window_5"] == best["entry_k_window_5"],
                "same_last_k_window_5": c["last_k_window_5_before_16_31"] == best["last_k_window_5_before_16_31"],
            }
        )
    return pd.DataFrame(rows).sort_values(["pair_score_32_63", "control_sample_id", "control_trajectory_id"])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    source = pd.read_csv(SOURCE)
    stage = build_stage(source)
    num = numeric_summary(stage)
    dist = distributions(stage)
    inv = invariants(stage)
    selectors = minimal_selector(stage)
    pairs = paired_examples(stage)

    stage.to_csv(OUT / "stage_32_63_comparison_table.csv", index=False)
    num.to_csv(OUT / "stage_32_63_numeric_summary.csv", index=False)
    dist.to_csv(OUT / "stage_32_63_distributions.csv", index=False)
    inv.to_csv(OUT / "stage_32_63_invariants.csv", index=False)
    selectors.to_csv(OUT / "minimal_selector_audit.csv", index=False)
    pairs.to_csv(OUT / "stage_32_63_paired_examples.csv", index=False)

    control = stage[stage["group"].eq("control_32_63_avoid_then_caught")]
    miss = stage[stage["group"].eq("miss_depth3_32_63_avoid")]
    perfect_selectors = selectors[selectors["separates_groups"].eq(True)]
    one_dim = perfect_selectors[perfect_selectors["dimension"].eq(1)]
    two_dim = perfect_selectors[perfect_selectors["dimension"].eq(2)]

    report = [
        "# 32-63 status split audit",
        "",
        "Finite-sample descriptive exploration only. No mechanism, proof, causality, or global Collatz claim is made.",
        "",
        "## Populations",
        "",
        f"- control 32-63 status rows: {len(control)}",
        f"- miss-depth-3 32-63 status rows: {len(miss)}",
        "",
        "## Main Read",
        "",
        "- The split is visible in `stage_chain_status`: controls are `32-63:avoid_then_caught`, miss-depth-3 rows are `32-63:avoid`.",
        "- But the local exit-event classification at 32-63 is not different: both groups are `avoid_then_caught` in `stage_event_classification`.",
        "- This means the split is not simply a different local lower-5pct event label. It is a chain-status distinction: in miss-depth-3, 32-63 is counted as part of a longer consecutive avoidance run; in controls, 32-63 already terminates as `avoid_then_caught` before the max-depth run begins at 16-31.",
        "- Local descriptors still differ in position and timing: controls have larger/longer 32-63 windows, while miss-depth-3 is closer to the 32-63 exit front.",
        "",
        "## Confirmed Differences",
        "",
        f"- 32-63 chain status: controls `{top_counts(control['stage_chain_status'])}`; miss-depth-3 `{top_counts(miss['stage_chain_status'])}`.",
        f"- entry_R: controls `{top_counts(control['entry_R'])}`; miss-depth-3 `{top_counts(miss['entry_R'])}`.",
        f"- exit_R: controls `{top_counts(control['exit_R'])}`; miss-depth-3 `{top_counts(miss['exit_R'])}`.",
        f"- wait length inside 32-63: controls `{top_counts(control['wait_length_inside_32_63'])}`; miss-depth-3 `{top_counts(miss['wait_length_inside_32_63'])}`.",
        f"- last event before 16-31: controls `{top_counts(control['last_event_before_16_31'])}`; miss-depth-3 `{top_counts(miss['last_event_before_16_31'])}`.",
        "",
        "## Confirmed Similarities",
        "",
        f"- local event classification: controls `{top_counts(control['stage_event_classification'])}`; miss-depth-3 `{top_counts(miss['stage_event_classification'])}`.",
        f"- next 16-31 stage class: controls `{top_counts(control['next_16_31_stage_class'])}`; miss-depth-3 `{top_counts(miss['next_16_31_stage_class'])}`.",
        f"- first event in 16-31 overlaps strongly: controls `{top_counts(control['first_event_in_16_31'])}`; miss-depth-3 `{top_counts(miss['first_event_in_16_31'])}`.",
        "",
        "## Minimal Selector Audit",
        "",
        f"- one-coordinate perfect selectors found: {len(one_dim)}",
        f"- two-coordinate perfect selectors found: {len(two_dim)}",
        "",
        md_table(selectors.head(20), max_rows=20),
        "",
        "## Numeric Summary",
        "",
        md_table(num, max_rows=40),
        "",
        "## Invariants And Near-Invariants",
        "",
        md_table(inv, max_rows=60),
        "",
        "## Paired Examples Preview",
        "",
        md_table(pairs, max_rows=12),
        "",
        "## Hypothesis Checks",
        "",
        "- Mostly position? Supported descriptively. `entry_R`, `exit_R`, and wait length differ strongly.",
        "- Mostly local shape? Weaker. Some local k/residue windows pair, but many local shape descriptors are not identical across groups.",
        "- Mostly k-sequence? Mixed. The groups share some recurring suffix-window motifs, but k-window selectors also separate subsets.",
        "- Mostly wait timing? Supported descriptively; controls show longer 32-63 windows.",
        "- Chain-status definition artifact? Partly yes. The local `stage_event_classification` is `avoid_then_caught` for both groups, while `stage_chain_status` differs. The meaningful finite-table split is therefore at the chain-status layer plus associated 32-63 position/timing descriptors, not a different local event classification alone.",
        "",
        "## Failed Hypotheses",
        "",
        "- `32-63 local event classification separates the groups`: false; it is `avoid_then_caught` for both groups.",
        "- `32-63 presence separates the groups`: false; both groups have the stage.",
        "- `A pure transition_k selector explains the split`: not supported; k values overlap.",
        "- `The split can be read as a mechanism`: not supported and not tested here.",
        "",
        "## Suggested Next Exploration",
        "",
        "- Pair the last 32-63 event before 16-31 with the first 16-31 event and inspect the boundary transition itself.",
        "- Stratify controls by the two main 32-63 entry windows, then compare whether the downstream 16-31/8-15 suffix remains invariant.",
        "- Keep the chain-status layer separate from the local event-classification layer in any manuscript wording.",
        "",
        "## Output Files",
        "",
        "- `stage_32_63_comparison_table.csv`",
        "- `stage_32_63_numeric_summary.csv`",
        "- `stage_32_63_distributions.csv`",
        "- `stage_32_63_invariants.csv`",
        "- `minimal_selector_audit.csv`",
        "- `stage_32_63_paired_examples.csv`",
    ]
    (OUT / "status_split_32_63_audit_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"control_rows={len(control)} miss_rows={len(miss)}")
    print(f"one_dim_selectors={len(one_dim)}")


if __name__ == "__main__":
    main()
