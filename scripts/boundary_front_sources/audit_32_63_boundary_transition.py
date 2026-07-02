from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Iterable

import pandas as pd


ROOT = Path(r"C:\Users\yauki\Documents\Codex\2026-07-01\new-chat")
STAGE32 = ROOT / "outputs" / "status_split_32_63_audit" / "stage_32_63_comparison_table.csv"
CHAIN_STAGE = ROOT / "outputs" / "s_minus_m_suffix_pairing" / "chain_stage_comparison_table.csv"
OUT = ROOT / "outputs" / "boundary_transition_32_63_audit"


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


def seq_prefix(value: object, n: int) -> str:
    if pd.isna(value) or str(value).strip() == "":
        return ""
    xs = [x.strip() for x in str(value).split(",") if x.strip()]
    return ",".join(xs[:n])


def boundary_selector_group(d: object) -> str:
    try:
        v = int(float(d))
    except Exception:
        return "other"
    if v in {0, 1}:
        return "lower_edge_0_1"
    if v in {2, 3, 4, 5, 7, 8}:
        return "miss_front_2_8_observed"
    return "other"


def build_boundary(stage: pd.DataFrame, chain: pd.DataFrame) -> pd.DataFrame:
    chain_cols = [
        "sample_id",
        "trajectory_id",
        "comparison_group",
        "16-31_entry_R",
        "16-31_entry_k",
        "16-31_entry_residue_pair_mod32",
        "16-31_exit_event_k_sequence",
        "16-31_eventually_caught_band",
        "16-31_classification",
        "8-15_entry_R",
        "8-15_entry_k",
        "8-15_entry_residue_pair_mod32",
        "8-15_exit_event_k_sequence",
        "8-15_eventually_caught_band",
        "8-15_classification",
        "4-7_entry_R",
        "4-7_entry_k",
        "4-7_entry_residue_pair_mod32",
        "4-7_exit_event_k_sequence",
        "4-7_classification",
    ]
    chain_small = chain[chain_cols].copy()
    df = stage.merge(chain_small, on=["sample_id", "trajectory_id"], how="left", suffixes=("", "_chain"))
    df["boundary_transition"] = (
        df["last_before_R"].astype("Int64").astype(str)
        + "->"
        + df["last_after_R"].astype("Int64").astype(str)
    )
    df["boundary_k"] = df["last_before_k"].astype("Int64").astype(str)
    df["boundary_residue_pair_mod32"] = df["last_before_residue_pair_mod32"]
    df["boundary_exit_distance"] = df["last_before_exit_distance"].astype("Int64")
    df["boundary_front_selector"] = df["boundary_exit_distance"].apply(boundary_selector_group)
    df["first_16_31"] = df["first_event_in_16_31"]
    df["first_16_31_R"] = pd.to_numeric(df["next_16_31_entry_R"], errors="coerce")
    df["first_16_31_k"] = pd.to_numeric(df["next_16_31_entry_k"], errors="coerce")
    for band in ["16-31", "8-15", "4-7"]:
        df[f"{band}_k_prefix_3"] = df[f"{band}_exit_event_k_sequence"].apply(lambda x: seq_prefix(x, 3))
        df[f"{band}_k_prefix_5"] = df[f"{band}_exit_event_k_sequence"].apply(lambda x: seq_prefix(x, 5))
    df["downstream_signature_16_8_4"] = (
        "16:"
        + df["16-31_k_prefix_5"].astype(str)
        + "|8:"
        + df["8-15_k_prefix_5"].astype(str)
        + "|4:"
        + df["4-7_k_prefix_5"].astype(str)
    )
    return df


def freq(df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    frames = []
    for feature in features:
        tmp = (
            df.groupby(["group", feature], dropna=False)
            .size()
            .reset_index(name="count")
            .rename(columns={feature: "value"})
        )
        tmp.insert(1, "feature", feature)
        frames.append(tmp)
    out = pd.concat(frames, ignore_index=True)
    return out.sort_values(["feature", "group", "count", "value"], ascending=[True, True, False, True])


def selector_audit(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for group, g in df.groupby("group"):
        rows.append(
            {
                "group": group,
                "rows": len(g),
                "lower_edge_0_1": int(g["boundary_front_selector"].eq("lower_edge_0_1").sum()),
                "miss_front_2_8_observed": int(g["boundary_front_selector"].eq("miss_front_2_8_observed").sum()),
                "other": int(g["boundary_front_selector"].eq("other").sum()),
                "selector_distribution": top_counts(g["boundary_front_selector"]),
            }
        )
    return pd.DataFrame(rows)


def reconvergence(df: pd.DataFrame) -> pd.DataFrame:
    features = [
        "first_16_31",
        "16-31_k_prefix_3",
        "16-31_k_prefix_5",
        "16-31_classification",
        "16-31_eventually_caught_band",
        "8-15_k_prefix_3",
        "8-15_k_prefix_5",
        "8-15_classification",
        "4-7_k_prefix_3",
        "4-7_classification",
        "downstream_signature_16_8_4",
    ]
    rows = []
    for feature in features:
        controls = set(df[df["group"].str.startswith("control")][feature].fillna("NA").astype(str))
        miss = set(df[df["group"].str.startswith("miss")][feature].fillna("NA").astype(str))
        intersection = controls & miss
        rows.append(
            {
                "feature": feature,
                "control_unique": len(controls),
                "miss_unique": len(miss),
                "shared_unique": len(intersection),
                "control_top": top_counts(df[df["group"].str.startswith("control")][feature], 5),
                "miss_top": top_counts(df[df["group"].str.startswith("miss")][feature], 5),
                "shared_values_preview": "; ".join(sorted(intersection)[:8]),
            }
        )
    return pd.DataFrame(rows)


def paired_examples(df: pd.DataFrame) -> pd.DataFrame:
    examples = []
    specs = [
        ("typical_control_32_to_29", "control_32_63_avoid_then_caught", "R=32->29|k=3|res=0->29"),
        ("rare_control_32_to_30", "control_32_63_avoid_then_caught", "R=32->30|k=2|res=0->30"),
        ("rare_control_33_to_31", "control_32_63_avoid_then_caught", "R=33->31|k=2|res=1->31"),
        ("typical_miss_35_to_31", "miss_depth3_32_63_avoid", "R=35->31|k=4|res=3->31"),
        ("typical_miss_36_to_31", "miss_depth3_32_63_avoid", "R=36->31|k=5|res=4->31"),
        ("miss_35_to_30", "miss_depth3_32_63_avoid", "R=35->30|k=5|res=3->30"),
        ("rare_miss_34_to_31", "miss_depth3_32_63_avoid", "R=34->31|k=3|res=2->31"),
        ("rare_miss_40_to_31", "miss_depth3_32_63_avoid", "R=40->31|k=9|res=8->31"),
    ]
    for label, group, event in specs:
        subset = df[df["group"].eq(group) & df["last_event_before_16_31"].eq(event)]
        if subset.empty:
            continue
        row = subset.sort_values(["sample_id", "trajectory_id"]).iloc[0]
        examples.append(
            {
                "example": label,
                "group": group,
                "sample_id": row["sample_id"],
                "trajectory_id": row["trajectory_id"],
                "boundary_event": row["last_event_before_16_31"],
                "boundary_exit_distance": row["boundary_exit_distance"],
                "wait_length_inside_32_63": row["wait_length_inside_32_63"],
                "first_16_31": row["first_16_31"],
                "16_31_k_prefix_5": row["16-31_k_prefix_5"],
                "8_15_k_prefix_5": row["8-15_k_prefix_5"],
                "4_7_k_prefix_5": row["4-7_k_prefix_5"],
                "lower5_final_status": row["lower5_final_status"],
            }
        )
    return pd.DataFrame(examples)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    stage = pd.read_csv(STAGE32)
    chain = pd.read_csv(CHAIN_STAGE)
    df = build_boundary(stage, chain)

    features = [
        "boundary_transition",
        "boundary_k",
        "boundary_residue_pair_mod32",
        "boundary_exit_distance",
        "boundary_front_selector",
        "first_16_31",
        "first_16_31_k",
        "16-31_k_prefix_3",
        "16-31_k_prefix_5",
        "8-15_k_prefix_3",
        "4-7_k_prefix_3",
    ]
    frequency = freq(df, features)
    selector = selector_audit(df)
    reconv = reconvergence(df)
    examples = paired_examples(df)

    df.to_csv(OUT / "boundary_transition_detail.csv", index=False)
    frequency.to_csv(OUT / "boundary_transition_frequency_table.csv", index=False)
    selector.to_csv(OUT / "simple_boundary_front_selector_audit.csv", index=False)
    reconv.to_csv(OUT / "downstream_reconvergence_table.csv", index=False)
    examples.to_csv(OUT / "boundary_transition_paired_examples.csv", index=False)

    control = df[df["group"].eq("control_32_63_avoid_then_caught")]
    miss = df[df["group"].eq("miss_depth3_32_63_avoid")]
    selector_ok = (
        control["boundary_front_selector"].eq("lower_edge_0_1").all()
        and miss["boundary_front_selector"].eq("miss_front_2_8_observed").all()
    )

    report = [
        "# 32-63 boundary-transition audit",
        "",
        "Finite-sample descriptive exploration only. Local event classification, chain status, and boundary-front position are kept separate.",
        "",
        "## Main Read",
        "",
        "- The simple boundary-front selector separates the two groups in this finite table.",
        f"- Selector result: `{selector_ok}`.",
        "- Controls leave 32-63 from the lower edge: mostly `R=32->29`, k=3, residue `0->29`.",
        "- Miss-depth-3 leaves 32-63 from the miss-front: mostly `R=35/36/37 -> 31/30`, k=4/5/6.",
        "- This is not a local event-classification split: both groups remain `stage_event_classification = avoid_then_caught` at 32-63.",
        "- Downstream does not immediately become identical. The first 16-31 event has overlap, but group-specific modes remain visible for several prefix summaries.",
        "",
        "## Exact Boundary Transition Frequencies",
        "",
        f"- controls boundary events: `{top_counts(control['last_event_before_16_31'])}`",
        f"- miss-depth-3 boundary events: `{top_counts(miss['last_event_before_16_31'])}`",
        "",
        "## Simple Selector Audit",
        "",
        md_table(selector),
        "",
        "Selector tested:",
        "",
        "- controls: `last_before_exit_distance in {0,1}`",
        "- miss-depth-3: `last_before_exit_distance in {2,3,4,5,7,8}`",
        "",
        "## Downstream Reconvergence",
        "",
        md_table(reconv),
        "",
        "## Paired Examples",
        "",
        md_table(examples),
        "",
        "## Failed Hypotheses",
        "",
        "- `transition_k alone is the split`: too narrow; k differs strongly at the boundary, but it is coupled to boundary-front position and residue.",
        "- `residue alone is the whole story`: too narrow; residue separates in this finite table, but it is the residue of the boundary-front event and tracks position.",
        "- `the two groups reconverge immediately after entering 16-31`: not fully supported; some first 16-31 shapes overlap, but prefix distributions remain visibly different.",
        "- `local event classification explains the split`: false; both groups have the same 32-63 local event classification.",
        "",
        "## Wording Recommendation",
        "",
        "A cautious manuscript sentence:",
        "",
        "> In the finite event table, the 32-63 split is best described as a boundary-front split rather than as a different local event-classification label: control trajectories leave 32-63 from the lower edge, usually `32->29`, whereas miss-depth-3 trajectories leave from the miss-front, most often `35/36/37 -> 31/30`, and remain in the consecutive avoidance run.",
        "",
        "Keep the following distinction explicit:",
        "",
        "- local event classification: both groups are `avoid_then_caught` at 32-63",
        "- chain status: controls are `avoid_then_caught`; miss-depth-3 rows are `avoid`",
        "- boundary-front coordinate: controls are `{0,1}` from the lower edge; miss-depth-3 rows are `{2,3,4,5,7,8}`",
        "",
        "## Output Files",
        "",
        "- `boundary_transition_detail.csv`",
        "- `boundary_transition_frequency_table.csv`",
        "- `simple_boundary_front_selector_audit.csv`",
        "- `downstream_reconvergence_table.csv`",
        "- `boundary_transition_paired_examples.csv`",
    ]
    (OUT / "boundary_transition_32_63_audit_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    print(f"wrote {OUT}")
    print(f"controls={len(control)} miss={len(miss)} selector_ok={selector_ok}")


if __name__ == "__main__":
    main()
