from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(r"C:\Users\yauki\Documents\Codex\2026-07-01\new-chat")
IN = ROOT / "outputs" / "band_general_boundary_front_audit" / "band_stage_boundary_detail.csv"
OUT = ROOT / "outputs" / "band_general_boundary_front_audit"

BAND_ORDER = ["4-7", "8-15", "16-31", "32-63", "64-127", "128-255", "256-511", "512-1023"]
FRONT_ORDER = ["lower_edge_front", "near_exit_front", "deeper_front", "unknown"]
STATUS_ORDER = ["avoid", "avoid_then_caught", "caught", "other", "NA"]


def esc(text: object) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def color_for(value: float, max_value: float, mode: str) -> str:
    if max_value <= 0 or value <= 0:
        return "#f7f7f5"
    t = min(1.0, value / max_value)
    if mode == "share":
        # green-blue scale
        r0, g0, b0 = (238, 247, 244)
        r1, g1, b1 = (31, 113, 118)
    else:
        # muted amber-red scale
        r0, g0, b0 = (250, 245, 235)
        r1, g1, b1 = (159, 76, 55)
    r = int(r0 + (r1 - r0) * t)
    g = int(g0 + (g1 - g0) * t)
    b = int(b0 + (b1 - b0) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def build_table(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["stage_chain_status"] = df["stage_chain_status"].fillna("NA").replace("", "NA")
    counts = (
        df.groupby(["band", "boundary_front_class", "stage_chain_status"], dropna=False)
        .size()
        .reset_index(name="count")
    )
    rows = []
    for band in BAND_ORDER:
        for front in FRONT_ORDER:
            sub = counts[counts["band"].eq(band) & counts["boundary_front_class"].eq(front)]
            if sub.empty:
                continue
            rec = {"band": band, "front": front}
            total = int(sub["count"].sum())
            rec["total"] = total
            seen = set()
            for status in STATUS_ORDER:
                if status == "other":
                    val = int(sub[~sub["stage_chain_status"].isin(STATUS_ORDER)]["count"].sum())
                else:
                    val = int(sub[sub["stage_chain_status"].eq(status)]["count"].sum())
                rec[status] = val
                seen.add(status)
            rows.append(rec)
    return pd.DataFrame(rows)


def write_csv(table: pd.DataFrame) -> None:
    table.to_csv(OUT / "band_front_chain_status_heatmap_table.csv", index=False)


def make_svg(table: pd.DataFrame, value_mode: str, out_path: Path) -> None:
    statuses = ["avoid", "avoid_then_caught", "caught", "other", "NA"]
    label_w = 230
    col_w = 128
    row_h = 34
    header_h = 78
    note_h = 54
    width = label_w + col_w * len(statuses) + 42
    height = header_h + row_h * len(table) + note_h
    max_value = 1.0 if value_mode == "share" else max(float(table[s].max()) for s in statuses)

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<style>text{font-family:Segoe UI,Arial,sans-serif;fill:#222}.small{font-size:11px}.label{font-size:12px}.head{font-size:13px;font-weight:600}.title{font-size:18px;font-weight:700}</style>',
        f'<text x="18" y="28" class="title">band × front × chain_status heatmap ({esc(value_mode)})</text>',
        '<text x="18" y="50" class="small">Finite-sample lower_5pct exit-event rows. Front classes are based on last_before_exit_distance.</text>',
    ]
    for j, status in enumerate(statuses):
        x = label_w + j * col_w
        lines.append(f'<text x="{x + col_w / 2}" y="72" text-anchor="middle" class="head">{esc(status)}</text>')

    y = header_h
    prev_band = None
    for _, row in table.iterrows():
        band = row["band"]
        front = row["front"]
        if band != prev_band:
            lines.append(f'<line x1="12" x2="{width - 14}" y1="{y}" y2="{y}" stroke="#d4d4cf" stroke-width="1"/>')
            prev_band = band
        lines.append(f'<text x="18" y="{y + 22}" class="label">{esc(band)} / {esc(front)}  n={int(row["total"])}</text>')
        total = max(1, int(row["total"]))
        for j, status in enumerate(statuses):
            raw = int(row[status])
            val = raw / total if value_mode == "share" else raw
            color = color_for(val, max_value, value_mode)
            x = label_w + j * col_w
            lines.append(f'<rect x="{x}" y="{y + 4}" width="{col_w - 6}" height="{row_h - 7}" rx="0" fill="{color}" stroke="#ffffff"/>')
            if value_mode == "share":
                label = f"{raw} ({val:.1%})" if raw else ""
            else:
                label = str(raw) if raw else ""
            if label:
                lines.append(f'<text x="{x + (col_w - 6) / 2}" y="{y + 23}" text-anchor="middle" class="small">{esc(label)}</text>')
        y += row_h
    lines.extend(
        [
            f'<text x="18" y="{height - 30}" class="small">count mode uses absolute cell counts; share mode normalizes within each band/front row.</text>',
            f'<text x="18" y="{height - 13}" class="small">No mechanism, causality, proof, or global Collatz behavior is implied.</text>',
            "</svg>",
        ]
    )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    df = pd.read_csv(IN)
    table = build_table(df)
    write_csv(table)
    make_svg(table, "count", OUT / "band_front_chain_status_heatmap_counts.svg")
    make_svg(table, "share", OUT / "band_front_chain_status_heatmap_share.svg")
    print(f"wrote {OUT / 'band_front_chain_status_heatmap_counts.svg'}")
    print(f"wrote {OUT / 'band_front_chain_status_heatmap_share.svg'}")
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
