from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Iterable

import pandas as pd


ROOT = Path(r"C:\Users\yauki\Documents\Codex\2026-07-01\new-chat")
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
OUT = ROOT / "outputs" / "band_general_boundary_front_audit"

BANDS = ["4-7", "8-15", "16-31", "32-63", "64-127", "128-255", "256-511", "512-1023"]


def as_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


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
        values = [str(row[c]).replace("|", "\\|") for c in cols]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def band_lower(band: str) -> int:
    return int(str(band).split("-", 1)[0])


def residue_pair_mod32(before: object, after: object) -> str:
    if pd.isna(before) or pd.isna(after):
        return ""
    return f"{int(before) % 32}->{int(after) % 32}"


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


def seq_list(value: object) -> list[str]:
    if pd.isna(value) or str(value).strip() == "":
        return []
    return [x.strip() for x in str(value).split(",") if x.strip()]


def last_seq_value(value: object) -> object:
    xs = seq_list(value)
    return xs[-1] if xs else pd.NA


def boundary_front_class(distance: object) -> str:
    try:
        d = int(float(distance))
    except Exception:
        return "unknown"
    if d in {0, 1}:
        return "lower_edge_front"
    if d in {2, 3, 4, 5, 6, 7, 8}:
        return "near_exit_front"
    if d > 8:
        return "deeper_front"
    return "unknown"


def front_purity(df: pd.DataFrame, predictor: str, target: str) -> float:
    if df.empty:
        return 0.0
    total = 0
    correct = 0
    for _, g in df.groupby(predictor, dropna=False):
        counts = g[target].fillna("NA").astype(str).value_counts()
        total += int(counts.sum())
        correct += int(counts.iloc[0])
    return round(correct / total, 6) if total else 0.0


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, set[tuple[str, int]]]:
    waiting = pd.read_csv(WAITING_DETAIL)
    exit_events = pd.read_csv(EXIT_EVENTS)
    chains = pd.read_csv(EXIT_CHAINS)
    for frame in [waiting, exit_events, chains]:
        if "trajectory_id" in frame.columns:
            frame["trajectory_id"] = as_num(frame["trajectory_id"]).astype("Int64")
    for col in ["event_index", "remaining_K_before", "remaining_K_after", "transition_k"]:
        waiting[col] = as_num(waiting[col])
    waiting["miss_event_bool"] = waiting["miss_event"].fillna(False).astype(bool)
    waiting["residue_pair_mod32"] = [
        residue_pair_mod32(a, b)
        for a, b in zip(waiting["remaining_K_before"], waiting["remaining_K_after"])
    ]
    miss_shapes = set(
        tuple(x)
        for x in waiting[waiting["miss_event_bool"]][["residue_pair_mod32", "transition_k"]]
        .dropna()
        .astype({"transition_k": int})
        .itertuples(index=False, name=None)
    )
    waiting["miss_supported_shape"] = [
        (r, int(k)) in miss_shapes if not pd.isna(k) else False
        for r, k in zip(waiting["residue_pair_mod32"], waiting["transition_k"])
    ]
    return waiting, exit_events, chains, miss_shapes


def waiting_aggregates(waiting: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (sample_id, trajectory_id, band), g in waiting.groupby(["sample_id", "trajectory_id", "band"], dropna=False):
        g = g.sort_values("event_index")
        near_counts = g["near_behavior"].fillna("NA").astype(str).value_counts()
        traj_counts = g["trajectory_behavior_class"].fillna("NA").astype(str).value_counts()
        rows.append(
            {
                "sample_id": sample_id,
                "trajectory_id": trajectory_id,
                "band": band,
                "waiting_rows": len(g),
                "miss_rows_in_band": int(g["miss_event_bool"].sum()),
                "miss_supported_shape_rows_in_band": int(g["miss_supported_shape"].sum()),
                "has_miss_event_in_band": bool(g["miss_event_bool"].any()),
                "has_miss_supported_shape_in_band": bool(g["miss_supported_shape"].any()),
                "near_behavior": top_counts(g["near_behavior"], 5),
                "dominant_near_behavior": near_counts.index[0] if not near_counts.empty else "NA",
                "trajectory_behavior_class": top_counts(g["trajectory_behavior_class"], 5),
                "dominant_trajectory_behavior_class": traj_counts.index[0] if not traj_counts.empty else "NA",
                "waiting_R_sequence_prefix": ",".join(str(int(x)) for x in g["remaining_K_before"].dropna().tolist()[:20]),
                "waiting_k_sequence_prefix": ",".join(str(int(x)) for x in g["transition_k"].dropna().tolist()[:20]),
            }
        )
    return pd.DataFrame(rows)


def build_detail(waiting: pd.DataFrame, exit_events: pd.DataFrame, chains: pd.DataFrame) -> pd.DataFrame:
    lower_events = exit_events[
        exit_events["exit_layer_id"].eq("lower_5pct") & exit_events["band"].isin(BANDS)
    ].copy()
    lower_chains = chains[chains["exit_layer_id"].eq("lower_5pct")].copy()
    lower_chains = lower_chains[
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
            "number_of_consecutive_bands_where_exit_layer_was_avoided": "max_avoidance_run_length",
            "avoidance_pattern_by_band": "chain_pattern_by_band",
            "avoidance_runs_by_band": "max_depth_run_bands",
        }
    )
    statuses = lower_chains["chain_pattern_by_band"].apply(parse_pattern)
    for band in BANDS:
        lower_chains[f"{band}_chain_status"] = statuses.apply(lambda d: d.get(band, ""))

    detail = lower_events.merge(waiting_aggregates(waiting), on=["sample_id", "trajectory_id", "band"], how="left")
    detail = detail.merge(lower_chains, on=["sample_id", "trajectory_id"], how="left")
    detail["stage_chain_status"] = [
        row.get(f"{row['band']}_chain_status", "") for _, row in detail.iterrows()
    ]
    detail["stage_event_classification"] = detail["classification"]
    detail["band_lower"] = detail["band"].apply(band_lower)
    detail["last_before_R"] = as_num(detail["min_remaining_K_in_band"])
    detail["boundary_k"] = detail["k_sequence_until_resolution"].apply(last_seq_value)
    detail["boundary_k_num"] = as_num(detail["boundary_k"])
    detail["last_after_R"] = detail["last_before_R"] - detail["boundary_k_num"]
    detail["last_before_exit_distance"] = detail["last_before_R"] - detail["band_lower"]
    detail["boundary_front_class"] = detail["last_before_exit_distance"].apply(boundary_front_class)
    detail["boundary_transition"] = (
        detail["last_before_R"].astype("Int64").astype(str)
        + "->"
        + detail["last_after_R"].astype("Int64").astype(str)
    )
    detail["boundary_residue_pair_mod32"] = [
        residue_pair_mod32(a, b) for a, b in zip(detail["last_before_R"], detail["last_after_R"])
    ]
    return detail


def grouped_count_table(detail: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "band",
        "boundary_front_class",
        "stage_chain_status",
        "stage_event_classification",
        "dominant_near_behavior",
        "dominant_trajectory_behavior_class",
        "max_avoidance_depth",
        "eventual_capture_band",
    ]
    return (
        detail.groupby(cols, dropna=False)
        .size()
        .reset_index(name="rows")
        .sort_values(["band", "boundary_front_class", "rows"], ascending=[True, True, False])
    )


def front_distribution(detail: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for band in BANDS:
        g = detail[detail["band"].eq(band)]
        if g.empty:
            rows.append(
                {
                    "band": band,
                    "front_class": "not_available",
                    "rows": 0,
                    "stage_chain_status": "NA",
                    "stage_event_classification": "NA",
                    "near_behavior": "NA",
                    "trajectory_behavior_class": "NA",
                    "max_avoidance_depth": "NA",
                    "eventual_capture_band": "NA",
                    "miss_rows": 0,
                    "miss_supported_shape_rows": 0,
                }
            )
            continue
        for front, f in g.groupby("boundary_front_class", dropna=False):
            rows.append(
                {
                    "band": band,
                    "front_class": front,
                    "rows": len(f),
                    "stage_chain_status": top_counts(f["stage_chain_status"], 6),
                    "stage_event_classification": top_counts(f["stage_event_classification"], 6),
                    "near_behavior": top_counts(f["dominant_near_behavior"], 6),
                    "trajectory_behavior_class": top_counts(f["dominant_trajectory_behavior_class"], 6),
                    "max_avoidance_depth": top_counts(f["max_avoidance_depth"], 6),
                    "eventual_capture_band": top_counts(f["eventual_capture_band"], 6),
                    "miss_rows": int(f["miss_rows_in_band"].fillna(0).sum()),
                    "miss_supported_shape_rows": int(f["miss_supported_shape_rows_in_band"].fillna(0).sum()),
                }
            )
    return pd.DataFrame(rows)


def boundary_transition_frequencies(detail: pd.DataFrame) -> pd.DataFrame:
    features = [
        "boundary_transition",
        "boundary_k",
        "boundary_residue_pair_mod32",
        "last_before_exit_distance",
        "stage_chain_status",
        "stage_event_classification",
        "dominant_near_behavior",
    ]
    frames = []
    for feature in features:
        tmp = (
            detail.groupby(["band", "boundary_front_class", feature], dropna=False)
            .size()
            .reset_index(name="count")
            .rename(columns={feature: "value"})
        )
        tmp.insert(2, "feature", feature)
        frames.append(tmp)
    return pd.concat(frames, ignore_index=True).sort_values(
        ["band", "boundary_front_class", "feature", "count"],
        ascending=[True, True, True, False],
    )


def compact_cross_band(detail: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for band in BANDS:
        g = detail[detail["band"].eq(band)]
        if g.empty:
            rows.append(
                {
                    "band": band,
                    "rows": 0,
                    "front_classes_present": "not_available",
                    "dominant_front": "NA",
                    "dominant_chain_by_front": "NA",
                    "dominant_local_class_by_front": "NA",
                    "dominant_near_behavior_by_front": "NA",
                    "miss_rows": 0,
                    "miss_supported_shape_rows": 0,
                    "front_purity_for_chain_status": 0,
                    "local_class_purity_for_chain_status": 0,
                    "front_better_than_local_class": False,
                    "notes": "no lower_5pct exit-event rows for this band",
                }
            )
            continue
        front_bits = []
        chain_bits = []
        local_bits = []
        near_bits = []
        for front, f in g.groupby("boundary_front_class", dropna=False):
            front_bits.append(f"{front}:{len(f)}")
            chain_bits.append(f"{front}=>{top_counts(f['stage_chain_status'], 3)}")
            local_bits.append(f"{front}=>{top_counts(f['stage_event_classification'], 3)}")
            near_bits.append(f"{front}=>{top_counts(f['dominant_near_behavior'], 3)}")
        front_p = front_purity(g, "boundary_front_class", "stage_chain_status")
        local_p = front_purity(g, "stage_event_classification", "stage_chain_status")
        miss_rows = int(g["miss_rows_in_band"].fillna(0).sum())
        miss_shape_rows = int(g["miss_supported_shape_rows_in_band"].fillna(0).sum())
        notes = []
        if miss_rows == 0:
            notes.append("no observed miss events in this band")
        if miss_shape_rows > 0:
            notes.append("miss-supported local shapes appear")
        else:
            notes.append("no miss-supported local shapes observed")
        if set(g["boundary_front_class"]) >= {"lower_edge_front", "near_exit_front"}:
            notes.append("lower/near front structure present")
        rows.append(
            {
                "band": band,
                "rows": len(g),
                "front_classes_present": "; ".join(front_bits),
                "dominant_front": g["boundary_front_class"].value_counts().index[0],
                "dominant_chain_by_front": " | ".join(chain_bits),
                "dominant_local_class_by_front": " | ".join(local_bits),
                "dominant_near_behavior_by_front": " | ".join(near_bits),
                "miss_rows": miss_rows,
                "miss_supported_shape_rows": miss_shape_rows,
                "front_purity_for_chain_status": front_p,
                "local_class_purity_for_chain_status": local_p,
                "front_better_than_local_class": front_p > local_p,
                "notes": "; ".join(notes),
            }
        )
    return pd.DataFrame(rows)


def write_report(
    compact: pd.DataFrame,
    front_dist: pd.DataFrame,
    grouped: pd.DataFrame,
    freq: pd.DataFrame,
) -> None:
    report = [
        "# Band-general boundary-front geometry audit",
        "",
        "Finite-sample descriptive geometry only. This audit does not require miss events to exist in a band and does not claim mechanism, causality, proof, counterexample, or global Collatz behavior.",
        "",
        "## Definitions",
        "",
        "- `lower_edge_front`: `last_before_exit_distance in {0,1}`",
        "- `near_exit_front`: `last_before_exit_distance in {2,3,4,5,6,7,8}`",
        "- `deeper_front`: `last_before_exit_distance > 8`",
        "- `last_before_exit_distance` is a boundary-aligned coordinate: `last_before_R - band_lower`.",
        "- `miss_supported_shape_rows` counts waiting-hall rows whose `(residue_pair_mod32, transition_k)` belongs to the observed miss-event shape support. This is a shape-support diagnostic, not a miss label.",
        "",
        "## Compact Cross-Band Table",
        "",
        md_table(compact),
        "",
        "## Main Read",
        "",
        "- The audit is now a boundary-front geometry audit, not a miss/control audit.",
        "- Bands with no miss events are kept in the table and interpreted only through front class, chain status, local event classification, near behavior, trajectory behavior, and shape support.",
        "- `front_purity_for_chain_status` and `local_class_purity_for_chain_status` are finite-table summaries of how well each coordinate groups the observed chain-status labels.",
        "",
        "## Per-Band Front Distribution",
        "",
        md_table(front_dist, max_rows=80),
        "",
        "## Count Table",
        "",
        md_table(grouped, max_rows=100),
        "",
        "## Boundary Transition Frequency Preview",
        "",
        md_table(freq, max_rows=120),
        "",
        "## Notes On Bands With No Miss Events",
        "",
    ]
    for row in compact.itertuples(index=False):
        if getattr(row, "miss_rows") == 0:
            report.append(f"- `{getattr(row, 'band')}`: {getattr(row, 'notes')}")
    report.extend(
        [
            "",
            "## Wording Recommendation",
            "",
            "> The cross-band audit should be phrased as a boundary-front geometry check, not as a miss/control replication test. Higher bands may contain no observed miss events; nevertheless, their lower-edge, near-exit, and deeper-front rows can be compared descriptively against chain status, local event classification, near behavior, and miss-supported local shape support. In this sense the question is whether the geometry of leaving a dyadic band is scale-stable, not whether miss events themselves recur at every scale.",
            "",
            "## Output Files",
            "",
            "- `band_stage_boundary_detail.csv`",
            "- `band_grouped_count_table.csv`",
            "- `band_front_distribution.csv`",
            "- `band_boundary_transition_frequencies.csv`",
            "- `band_compact_cross_band_table.csv`",
        ]
    )
    (OUT / "band_general_boundary_front_audit_report.md").write_text(
        "\n".join(report) + "\n", encoding="utf-8"
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    waiting, exit_events, chains, miss_shapes = load_inputs()
    detail = build_detail(waiting, exit_events, chains)
    grouped = grouped_count_table(detail)
    front_dist = front_distribution(detail)
    freq = boundary_transition_frequencies(detail)
    compact = compact_cross_band(detail)

    detail.to_csv(OUT / "band_stage_boundary_detail.csv", index=False)
    grouped.to_csv(OUT / "band_grouped_count_table.csv", index=False)
    front_dist.to_csv(OUT / "band_front_distribution.csv", index=False)
    freq.to_csv(OUT / "band_boundary_transition_frequencies.csv", index=False)
    compact.to_csv(OUT / "band_compact_cross_band_table.csv", index=False)
    write_report(compact, front_dist, grouped, freq)

    print(f"wrote {OUT}")
    print(f"miss_shape_support_size={len(miss_shapes)}")
    print(compact.to_string(index=False))


if __name__ == "__main__":
    main()
