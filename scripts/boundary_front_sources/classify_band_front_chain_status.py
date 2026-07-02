from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(r"C:\Users\yauki\Documents\Codex\2026-07-01\new-chat")
IN = ROOT / "outputs" / "band_general_boundary_front_audit" / "band_front_chain_status_heatmap_table.csv"
OUT = ROOT / "outputs" / "band_general_boundary_front_audit"


def share(value: int, total: int) -> float:
    return 0.0 if total == 0 else value / total


def classify(row: pd.Series) -> str:
    total = int(row["total"])
    avoid = int(row["avoid"])
    atc = int(row["avoid_then_caught"])
    caught = int(row["caught"])
    if total == 0:
        return "not_available"
    if caught / total >= 0.5 and avoid == 0:
        return "capture_layer"
    if avoid / total >= 0.95:
        return "avoid_front"
    if atc / total >= 0.90 and avoid == 0:
        return "resolved_front"
    if (atc + caught) / total >= 0.90 and avoid == 0:
        return "resolved_or_caught_front"
    if avoid > 0 and atc > 0:
        return "mixed_avoid_resolved_front"
    return "mixed_front"


def main() -> None:
    df = pd.read_csv(IN)
    rows = []
    for _, row in df.iterrows():
        total = int(row["total"])
        avoid = int(row["avoid"])
        atc = int(row["avoid_then_caught"])
        caught = int(row["caught"])
        rows.append(
            {
                "band": row["band"],
                "boundary_front": row["front"],
                "rows": total,
                "avoid": avoid,
                "avoid_then_caught": atc,
                "caught": caught,
                "avoid_share": round(share(avoid, total), 4),
                "resolved_share": round(share(atc + caught, total), 4),
                "front_role": classify(row),
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "band_front_chain_status_classification.csv", index=False)

    md = [
        "# Band x BoundaryFront x ChainStatus classification",
        "",
        "Finite-sample descriptive classification only. No mechanism, proof, causality, or global Collatz behavior is claimed.",
        "",
        "| band | boundary_front | rows | avoid | avoid_then_caught | caught | avoid_share | resolved_share | front_role |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for _, row in out.iterrows():
        md.append(
            f"| {row['band']} | {row['boundary_front']} | {row['rows']} | {row['avoid']} | "
            f"{row['avoid_then_caught']} | {row['caught']} | {row['avoid_share']:.4f} | "
            f"{row['resolved_share']:.4f} | {row['front_role']} |"
        )
    md.extend(
        [
            "",
            "## Role legend",
            "",
            "- `capture_layer`: caught-dominant lower layer.",
            "- `avoid_front`: avoid-dominant front.",
            "- `resolved_front`: avoid_then_caught-dominant front.",
            "- `resolved_or_caught_front`: no avoid; resolved/caught mixture.",
            "- `mixed_avoid_resolved_front`: avoid and resolved states both present.",
            "- `mixed_front`: no single dominant role under the simple thresholds.",
        ]
    )
    (OUT / "band_front_chain_status_classification.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
