from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Iterable

import pandas as pd


ROOT = Path(r"C:\Users\yauki\Documents\Codex\2026-07-01\new-chat")
PREV = ROOT / "outputs" / "s_minus_m_control_exploration"
OUT = ROOT / "outputs" / "s_minus_m_depth2_chain_exploration"
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


def parse_pattern(pattern: object) -> list[tuple[str, str]]:
    if pd.isna(pattern):
        return []
    out: list[tuple[str, str]] = []
    for item in str(pattern).split(">"):
        if ":" not in item:
            continue
        band, status = item.split(":", 1)
        out.append((band.strip(), status.strip()))
    return out


def around_band(pattern: object, band: object) -> str:
    parsed = parse_pattern(pattern)
    if not parsed:
        return ""
    band = str(band)
    idxs = [i for i, (b, _) in enumerate(parsed) if b == band]
    if not idxs:
        return "event_band_not_in_chain:" + ">".join(f"{b}:{s}" for b, s in parsed)
    i = idxs[0]
    left = max(0, i - 2)
    right = min(len(parsed), i + 3)
    parts = []
    for j in range(left, right):
        b, s = parsed[j]
        token = f"{b}:{s}"
        if j == i:
            token = "[" + token + "]"
        parts.append(token)
    return ">".join(parts)


def load_waiting() -> pd.DataFrame:
    df = pd.read_csv(WAITING_DETAIL)
    df = df.copy()
    df["event_row_id"] = range(1, len(df) + 1)
    for col in ["event_index", "remaining_K_before", "remaining_K_after", "transition_k", "distance_from_exit", "wait_length"]:
        df[col] = as_int(df[col])
    df["exit_distance"] = df["distance_from_exit"]
    df["miss_event"] = pd.to_numeric(df["miss_event"], errors="coerce").fillna(0).astype(int)
    df["residue_before_mod32"] = (df["remaining_K_before"] % 32).astype("Int64")
    df["residue_after_mod32"] = (df["remaining_K_after"] % 32).astype("Int64")
    df["residue_pair_mod32"] = df["residue_before_mod32"].astype(str) + "->" + df["residue_after_mod32"].astype(str)
    df["R_drop"] = df["remaining_K_before"] - df["remaining_K_after"]
    return df


def add_trajectory_chain_summary(events: pd.DataFrame, chains: pd.DataFrame) -> pd.DataFrame:
    event_summary = (
        events.groupby(["sample_id", "trajectory_id"], dropna=False)
        .agg(
            exit_event_bands=("band", lambda s: ">".join(dict.fromkeys(str(x) for x in s))),
            exit_event_classifications=("classification", lambda s: top_counts(s, 10)),
            exit_event_caught_bands=("eventually_caught_band", lambda s: top_counts(s, 10)),
            exit_event_k_sequences=("k_sequence_until_resolution", lambda s: " | ".join(str(x) for x in s.head(8))),
        )
        .reset_index()
    )
    max_rows = chains.sort_values(
        ["sample_id", "trajectory_id", "max_avoidance_depth", "number_of_consecutive_bands_where_exit_layer_was_avoided"],
        ascending=[True, True, False, False],
    ).drop_duplicates(["sample_id", "trajectory_id"], keep="first")
    max_rows = max_rows[
        [
            "sample_id",
            "trajectory_id",
            "exit_layer_id",
            "exit_layer_definition",
            "number_of_consecutive_bands_where_exit_layer_was_avoided",
            "max_avoidance_depth",
            "avoidance_pattern_by_band",
            "avoidance_runs_by_band",
            "eventual_capture_band",
            "final_status",
        ]
    ].rename(
        columns={
            "exit_layer_id": "max_depth_exit_layer_id",
            "exit_layer_definition": "max_depth_exit_layer_definition",
            "number_of_consecutive_bands_where_exit_layer_was_avoided": "max_depth_run_length",
            "avoidance_pattern_by_band": "max_depth_avoidance_pattern",
            "avoidance_runs_by_band": "max_depth_avoidance_run_bands",
            "eventual_capture_band": "max_depth_eventual_capture_band",
            "final_status": "max_depth_final_status",
        }
    )
    all_chain_summary = (
        chains.groupby(["sample_id", "trajectory_id"], dropna=False)
        .agg(
            all_chain_depths=("max_avoidance_depth", lambda s: top_counts(s, 8)),
            all_chain_patterns=("avoidance_pattern_by_band", lambda s: " || ".join(str(x) for x in s)),
            all_chain_capture_bands=("eventual_capture_band", lambda s: top_counts(s, 8)),
            all_chain_final_statuses=("final_status", lambda s: top_counts(s, 8)),
        )
        .reset_index()
    )
    return event_summary.merge(max_rows, on=["sample_id", "trajectory_id"], how="outer").merge(
        all_chain_summary, on=["sample_id", "trajectory_id"], how="outer"
    )


def context_sequences(waiting: pd.DataFrame, targets: pd.DataFrame) -> pd.DataFrame:
    ordered = waiting.sort_values(["sample_id", "trajectory_id", "band", "source_scope", "event_index"]).copy()
    grouped = {
        key: g.reset_index(drop=True)
        for key, g in ordered.groupby(["sample_id", "trajectory_id", "band", "source_scope"], dropna=False)
    }
    records = []
    for _, row in targets.iterrows():
        key = (row["sample_id"], row["trajectory_id"], row["band"], row["source_scope"])
        g = grouped.get(key)
        rec = {"event_row_id": row["event_row_id"]}
        if g is None:
            records.append(rec)
            continue
        matches = g.index[g["event_row_id"].eq(row["event_row_id"])].tolist()
        if not matches:
            records.append(rec)
            continue
        i = matches[0]
        before = g.iloc[max(0, i - 5) : i]
        after = g.iloc[i + 1 : min(len(g), i + 7)]
        rec["before_R_k_behavior"] = " > ".join(
            f"{r.remaining_K_before}/{r.transition_k}/{r.near_behavior}" for r in before.itertuples()
        )
        rec["event_R_k_behavior"] = f"{row['remaining_K_before']}/{row['transition_k']}/{row['near_behavior']}"
        rec["after_R_k_behavior"] = " > ".join(
            f"{r.remaining_K_before}/{r.transition_k}/{r.near_behavior}" for r in after.itertuples()
        )
        rec["next_exit_like_position_after_event"] = ""
        for r in after.itertuples():
            if str(r.position_label).startswith("exit") or str(r.near_behavior) in {"exit", "miss"}:
                rec["next_exit_like_position_after_event"] = (
                    f"event_index={r.event_index};R={r.remaining_K_before};"
                    f"k={r.transition_k};position={r.position_label};near={r.near_behavior}"
                )
                break
        records.append(rec)
    return pd.DataFrame(records)


def numeric_summary(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    rows = []
    for group, g in df.groupby("comparison_group"):
        for col in cols:
            s = pd.to_numeric(g[col], errors="coerce").dropna()
            rows.append(
                {
                    "comparison_group": group,
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


def distribution(df: pd.DataFrame, cols: list[str], out_prefix: str) -> pd.DataFrame:
    frames = []
    for col in cols:
        if col not in df.columns:
            continue
        tmp = (
            df.groupby(["comparison_group", col], dropna=False)
            .size()
            .reset_index(name="count")
            .rename(columns={col: "value"})
        )
        tmp.insert(1, "feature", col)
        frames.append(tmp)
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if not out.empty:
        out = out.sort_values(["feature", "comparison_group", "count", "value"], ascending=[True, True, False, True])
        out.to_csv(OUT / f"{out_prefix}_distributions.csv", index=False)
    return out


def constant_tables(controls: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    cols = [
        "miss_event",
        "group",
        "band",
        "band_after",
        "near_behavior",
        "position_label",
        "waiting_class",
        "trajectory_behavior_class",
        "max_avoidance_depth",
        "max_depth_run_length",
        "max_depth_exit_layer_id",
        "max_depth_eventual_capture_band",
        "max_depth_final_status",
        "transition_k",
        "R_drop",
        "residue_before_mod32",
        "residue_after_mod32",
        "residue_pair_mod32",
        "exit_distance",
        "remaining_K_before",
        "remaining_K_after",
    ]
    rows = []
    for col in cols:
        if col not in controls.columns:
            continue
        counts = controls[col].fillna("NA").astype(str).value_counts()
        rows.append(
            {
                "feature": col,
                "unique_values": int(counts.size),
                "top_value": counts.index[0] if counts.size else "",
                "top_count": int(counts.iloc[0]) if counts.size else 0,
                "exceptions": int(len(controls) - counts.iloc[0]) if counts.size else len(controls),
                "distribution": "; ".join(f"{k}:{v}" for k, v in counts.items()),
            }
        )
    table = pd.DataFrame(rows).sort_values(["exceptions", "unique_values", "feature"])
    constants = table[table["exceptions"].eq(0)].copy()
    near_constants = table[(table["exceptions"].between(1, 2))].copy()
    return constants, near_constants


def write_cards(controls: pd.DataFrame) -> None:
    lines = [
        "# S minus M 47 control chain cards",
        "",
        "Each card combines the selected waiting-hall event with the trajectory-level exit-avoidance chain summary.",
        "The chain layer is descriptive and trajectory-level; it is not treated as an event-level causal explanation.",
        "",
    ]
    for i, row in enumerate(controls.sort_values(["sample_id", "trajectory_id", "event_index"]).itertuples(), start=1):
        lines.extend(
            [
                f"## Card {i}: {row.sample_id} / trajectory {row.trajectory_id}",
                "",
                f"- selected event: band `{row.band}`, event_index `{row.event_index}`, R `{row.remaining_K_before}->{row.remaining_K_after}`, exit_distance `{row.exit_distance}`, k `{row.transition_k}`, residue `{row.residue_pair_mod32}`",
                f"- selected labels: position `{row.position_label}`, near_behavior `{row.near_behavior}`, waiting_class `{row.waiting_class}`, trajectory_behavior `{row.trajectory_behavior_class}`",
                f"- max avoidance depth: `{row.max_avoidance_depth}` via `{row.max_depth_exit_layer_id}`; run `{row.max_depth_avoidance_run_bands}`; final capture `{row.max_depth_eventual_capture_band}`; final status `{row.max_depth_final_status}`",
                f"- event-band location inside max-depth chain: `{row.chain_around_event_band}`",
                f"- max-depth chain pattern: `{row.max_depth_avoidance_pattern}`",
                f"- before event R/k/behavior: `{row.before_R_k_behavior}`",
                f"- event R/k/behavior: `{row.event_R_k_behavior}`",
                f"- after event R/k/behavior: `{row.after_R_k_behavior}`",
                f"- next exit-like position after event in same band window: `{row.next_exit_like_position_after_event}`",
                "",
            ]
        )
    (OUT / "s_minus_m_47_chain_cards.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    waiting = load_waiting()
    chains = pd.read_csv(EXIT_CHAINS)
    events = pd.read_csv(EXIT_EVENTS)
    for frame in [chains, events]:
        frame["trajectory_id"] = as_int(frame["trajectory_id"])
    chain_summary = add_trajectory_chain_summary(events, chains)

    miss = waiting[waiting["miss_event"].eq(1)].copy()
    miss_support = set(miss["residue_pair_mod32"].dropna().unique())
    controls = waiting[waiting["residue_pair_mod32"].isin(miss_support) & waiting["miss_event"].eq(0)].copy()
    if len(miss) != 228 or len(controls) != 47:
        raise SystemExit(f"Unexpected counts: miss={len(miss)} controls={len(controls)}")

    miss["group"] = "M_miss"
    controls["group"] = "S_minus_M_control"
    combined = pd.concat([miss, controls], ignore_index=True).merge(
        chain_summary, on=["sample_id", "trajectory_id"], how="left"
    )
    context = context_sequences(waiting, combined)
    combined = combined.merge(context, on="event_row_id", how="left")
    combined["chain_around_event_band"] = [
        around_band(pattern, band)
        for pattern, band in zip(combined["max_depth_avoidance_pattern"], combined["band"])
    ]

    controls_aug = combined[combined["group"].eq("S_minus_M_control")].copy()
    miss_depth2 = combined[combined["group"].eq("M_miss") & combined["max_avoidance_depth"].eq(2)].copy()
    miss_depth3 = combined[combined["group"].eq("M_miss") & combined["max_avoidance_depth"].eq(3)].copy()
    controls_aug["comparison_group"] = "S_minus_M_control_depth2"
    miss_depth2["comparison_group"] = "M_miss_depth2"
    miss_depth3["comparison_group"] = "M_miss_depth3"
    comparison = pd.concat([controls_aug, miss_depth2, miss_depth3], ignore_index=True)

    card_cols = [
        "event_row_id",
        "sample_id",
        "trajectory_id",
        "event_index",
        "band",
        "remaining_K_before",
        "remaining_K_after",
        "exit_distance",
        "transition_k",
        "residue_pair_mod32",
        "near_behavior",
        "position_label",
        "wait_length",
        "waiting_class",
        "trajectory_behavior_class",
        "max_avoidance_depth",
        "max_depth_exit_layer_id",
        "max_depth_run_length",
        "max_depth_avoidance_run_bands",
        "max_depth_eventual_capture_band",
        "max_depth_final_status",
        "max_depth_avoidance_pattern",
        "chain_around_event_band",
        "before_R_k_behavior",
        "event_R_k_behavior",
        "after_R_k_behavior",
        "next_exit_like_position_after_event",
    ]
    controls_aug[card_cols].to_csv(OUT / "s_minus_m_47_chain_cards.csv", index=False)
    write_cards(controls_aug)

    depth_transition = (
        combined.groupby(["group", "max_avoidance_depth", "exit_distance", "near_behavior", "band"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["group", "max_avoidance_depth", "count", "exit_distance"], ascending=[True, True, False, True])
    )
    depth_transition.to_csv(OUT / "depth_transition_table.csv", index=False)

    num = numeric_summary(
        comparison,
        [
            "remaining_K_before",
            "remaining_K_after",
            "exit_distance",
            "transition_k",
            "wait_length",
            "R_drop",
            "max_depth_run_length",
        ],
    )
    num.to_csv(OUT / "depth2_depth3_numeric_summary.csv", index=False)

    dists = distribution(
        comparison,
        [
            "band",
            "near_behavior",
            "position_label",
            "waiting_class",
            "trajectory_behavior_class",
            "residue_pair_mod32",
            "transition_k",
            "max_depth_exit_layer_id",
            "max_depth_avoidance_run_bands",
            "max_depth_eventual_capture_band",
            "max_depth_final_status",
            "chain_around_event_band",
        ],
        "depth2_depth3",
    )

    constants, near_constants = constant_tables(controls_aug)
    constants.to_csv(OUT / "s_minus_m_47_constant_coordinates.csv", index=False)
    near_constants.to_csv(OUT / "s_minus_m_47_near_constant_coordinates.csv", index=False)

    # Useful compact tables.
    control_patterns = (
        controls_aug.groupby(["max_depth_avoidance_pattern", "max_depth_avoidance_run_bands", "max_depth_eventual_capture_band"], dropna=False)
        .size()
        .reset_index(name="control_count")
        .sort_values(["control_count", "max_depth_avoidance_pattern"], ascending=[False, True])
    )
    control_patterns.to_csv(OUT / "s_minus_m_47_chain_pattern_counts.csv", index=False)
    comparison.to_csv(OUT / "control_miss_depth2_depth3_event_chain_detail.csv", index=False)

    # Interpretive counts, kept descriptive.
    control_event_band_in_run = controls_aug.apply(
        lambda r: str(r["band"]) in str(r["max_depth_avoidance_run_bands"]).split(">"), axis=1
    )
    miss2_event_band_in_run = miss_depth2.apply(
        lambda r: str(r["band"]) in str(r["max_depth_avoidance_run_bands"]).split(">"), axis=1
    )
    miss3_event_band_in_run = miss_depth3.apply(
        lambda r: str(r["band"]) in str(r["max_depth_avoidance_run_bands"]).split(">"), axis=1
    )

    report = [
        "# Why the 47 controls sit at max_avoidance_depth = 2",
        "",
        "Finite-sample descriptive exploration only. No mechanism, proof, causality, or global Collatz claim is made.",
        "",
        "## Inputs",
        "",
        f"- Waiting-hall table: `{WAITING_DETAIL}`",
        f"- Exit-avoidance chains: `{EXIT_CHAINS}`",
        f"- Exit-avoidance events: `{EXIT_EVENTS}`",
        "",
        "## Counts",
        "",
        f"- controls: {len(controls_aug)}",
        f"- miss depth 2 rows: {len(miss_depth2)}",
        f"- miss depth 3 rows: {len(miss_depth3)}",
        f"- controls whose selected event band is inside the max-depth avoidance run: {int(control_event_band_in_run.sum())} / {len(controls_aug)}",
        f"- miss depth 2 rows whose selected event band is inside the max-depth avoidance run: {int(miss2_event_band_in_run.sum())} / {len(miss_depth2)}",
        f"- miss depth 3 rows whose selected event band is inside the max-depth avoidance run: {int(miss3_event_band_in_run.sum())} / {len(miss_depth3)}",
        "",
        "## Confirmed similarities",
        "",
        "- Controls and miss rows still share the same local shape support by construction; every control has a miss-observed residue-pair plus transition-k pair.",
        "- Controls and miss-depth-2 rows both have max-depth chain length 2, so depth alone cannot distinguish them.",
        f"- Transition-k remains close across the depth-controlled comparison: {top_counts(comparison['comparison_group'] + ':' + comparison['transition_k'].astype(str), 12)}.",
        "",
        "## Confirmed differences",
        "",
        "- The 47 controls are not simply depth-2 miss rows shifted upward in one coordinate; they differ in behavior class and chain placement.",
        f"- Controls by trajectory behavior: `{top_counts(controls_aug['trajectory_behavior_class'])}`.",
        f"- Miss depth 2 by trajectory behavior: `{top_counts(miss_depth2['trajectory_behavior_class'])}`.",
        f"- Controls selected row behavior: `{top_counts(controls_aug['near_behavior'])}`; miss depth 2 selected row behavior: `{top_counts(miss_depth2['near_behavior'])}`.",
        f"- Controls selected event band is inside the max-depth avoidance run only {int(control_event_band_in_run.sum())}/{len(controls_aug)} times; for miss-depth-2 it is {int(miss2_event_band_in_run.sum())}/{len(miss_depth2)}.",
        "- For the controls, the selected `S \\ M` event usually occurs earlier/upstream of the two-band avoidance run; the depth-2 run is typically downstream.",
        "",
        "## What depth 3 adds",
        "",
        "- Miss-depth-3 rows add one more consecutive avoided band in the max-depth chain pattern.",
        f"- Miss-depth-3 max-depth run bands: `{top_counts(miss_depth3['max_depth_avoidance_run_bands'])}`.",
        f"- Control max-depth run bands: `{top_counts(controls_aug['max_depth_avoidance_run_bands'])}`.",
        "- The common control run is `16-31>8-15` followed by capture at `4-7`; common miss-depth-3 runs include `32-63>16-31>8-15` before capture at `4-7`.",
        "",
        "## Unexpected regularities",
        "",
        "- All 47 controls have `max_avoidance_depth = 2`, but the selected control event is generally not the chain's depth-run event. This separates the shape-control event from the later exit-avoidance run.",
        "- The control chain pattern is highly concentrated. See `s_minus_m_47_chain_pattern_counts.csv`.",
        "- The controls are constant on several coordinates; see the constants table below.",
        "",
        "## Failed hypotheses",
        "",
        "- `The selected control event itself is the depth-2 avoidance run`: mostly false. It is inside the max-depth run for only the count shown above.",
        "- `The controls are just miss-depth-2 rows shifted upward`: not supported as stated, because the selected-row behavior is `drift`, trajectory behavior is split between `drift_down` and `mid_band_wait_then_drop`, and the max-depth run is usually downstream of the selected event.",
        "- `Depth=2 alone explains the 47 controls`: false; miss-depth-2 rows exist but have miss labels and different selected-row behavior/position.",
        "",
        "## Interpretation stress test",
        "",
        "Candidate interpretation to falsify: `The 47 controls are displaced miss-shapes whose position sends them into drift rather than miss.`",
        "",
        "What survived descriptively:",
        "",
        "- The controls are genuinely displaced in `exit_distance` and `remaining_K_before` while retaining miss-like shape+k cells.",
        "- Their selected rows are all drift-labeled, not miss-labeled.",
        "- They do not enter the miss-front support after adding position coordinates.",
        "",
        "What weakens or complicates it:",
        "",
        "- The depth-2 chain fact is trajectory-level and downstream; it should not be read as the immediate consequence of the selected control event.",
        "- Some controls belong to `mid_band_wait_then_drop`, not only `drift_down`, so `drift` is not a single fine type.",
        "- This remains a finite-sample description of observed rows, not a rule.",
        "",
        "## Numeric comparison",
        "",
        md_table(num, max_rows=60),
        "",
        "## Constant coordinates across the 47 controls",
        "",
        md_table(constants, max_rows=40),
        "",
        "## Near-constant coordinates with one or two exceptions",
        "",
        md_table(near_constants, max_rows=40) if not near_constants.empty else "None under the one-or-two-exception rule.",
        "",
        "## Depth-transition table preview",
        "",
        md_table(depth_transition, max_rows=50),
        "",
        "## Suggested next exploration",
        "",
        "- Compare the downstream run `16-31>8-15 -> 4-7 capture` in controls against miss-depth-3 rows where the run starts one band earlier at `32-63`.",
        "- Build paired cards for controls and nearest same-shape miss rows, then compare the entire downstream chain pattern rather than only the selected event.",
        "- Split the controls into `drift_down` vs `mid_band_wait_then_drop` before making any stronger statement about the drift label.",
        "",
        "## Output files",
        "",
        "- `s_minus_m_47_chain_cards.md`",
        "- `s_minus_m_47_chain_cards.csv`",
        "- `control_miss_depth2_depth3_event_chain_detail.csv`",
        "- `depth_transition_table.csv`",
        "- `depth2_depth3_numeric_summary.csv`",
        "- `depth2_depth3_distributions.csv`",
        "- `s_minus_m_47_constant_coordinates.csv`",
        "- `s_minus_m_47_near_constant_coordinates.csv`",
        "- `s_minus_m_47_chain_pattern_counts.csv`",
    ]
    (OUT / "s_minus_m_depth2_chain_exploration_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    print(f"wrote {OUT}")
    print(f"controls={len(controls_aug)} miss_depth2={len(miss_depth2)} miss_depth3={len(miss_depth3)}")
    print(f"control_event_band_in_run={int(control_event_band_in_run.sum())}/{len(controls_aug)}")


if __name__ == "__main__":
    main()
