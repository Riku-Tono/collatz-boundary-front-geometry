from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageColor, ImageDraw, ImageFont


ROOT = Path(r"C:\Users\yauki\Documents\Codex\2026-07-01\csv-collatz-state-band-boundary-front")
OUT = ROOT / "outputs" / "empirical_flow_map"
SRC_DIR = Path(r"C:\Users\yauki\Documents\design\collatz\boundary-front geometry\boundary-front-geometry\csv")
STAGE_CSV = SRC_DIR / "band_stage_boundary_detail.csv"
EVENT_CSV = SRC_DIR / "miss_and_control_event_detail.csv"


STATE_COLS = ["band", "boundary_front", "chain_status"]
BAND_ORDER = [
    "0-1",
    "2-3",
    "4-7",
    "8-15",
    "16-31",
    "32-63",
    "64-127",
    "128-255",
    "256-511",
    "512-1023",
    "1024-2047",
]


def clean_text(value: object) -> str:
    if pd.isna(value):
        return "NA"
    text = str(value).strip()
    return text if text else "NA"


def state_label(row: pd.Series, prefix: str = "") -> str:
    return (
        f"{clean_text(row[prefix + 'band'])}|"
        f"{clean_text(row[prefix + 'boundary_front'])}|"
        f"{clean_text(row[prefix + 'chain_status'])}"
    )


def entropy_from_counts(counts: pd.Series) -> float:
    total = counts.sum()
    if total <= 0:
        return 0.0
    probs = counts / total
    return float(-(probs * np.log2(probs)).sum())


def distribution_string(counts: pd.Series, limit: int = 8) -> str:
    parts = []
    total = int(counts.sum())
    for key, count in counts.sort_values(ascending=False).head(limit).items():
        parts.append(f"{key}:{int(count)} ({count / total:.3f})")
    if len(counts) > limit:
        parts.append(f"other_states:{int(counts.iloc[limit:].sum())} ({counts.iloc[limit:].sum() / total:.3f})")
    return "; ".join(parts)


def sort_band_key(band: str) -> tuple[int, str]:
    if band in BAND_ORDER:
        return (BAND_ORDER.index(band), band)
    return (len(BAND_ORDER), band)


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


def wrap_label(text: str, width: int = 24) -> str:
    parts = text.split("|")
    lines = []
    for part in parts:
        if len(part) <= width:
            lines.append(part)
        else:
            lines.append(part[: width - 1] + ".")
    return "\n".join(lines)


def blend_hex(c1: str, c2: str, t: float) -> tuple[int, int, int]:
    a = np.array(ImageColor.getrgb(c1), dtype=float)
    b = np.array(ImageColor.getrgb(c2), dtype=float)
    return tuple(np.round(a * (1 - t) + b * t).astype(int))


def draw_arrow(draw: ImageDraw.ImageDraw, p1: tuple[float, float], p2: tuple[float, float], fill, width: int = 2) -> None:
    x1, y1 = p1
    x2, y2 = p2
    draw.line((x1, y1, x2, y2), fill=fill, width=width)
    angle = math.atan2(y2 - y1, x2 - x1)
    head = 12 + width
    spread = 0.45
    a1 = angle + math.pi - spread
    a2 = angle + math.pi + spread
    pts = [
        (x2, y2),
        (x2 + head * math.cos(a1), y2 + head * math.sin(a1)),
        (x2 + head * math.cos(a2), y2 + head * math.sin(a2)),
    ]
    draw.polygon(pts, fill=fill)


def prepare_stage_rows() -> pd.DataFrame:
    df = pd.read_csv(STAGE_CSV)
    df = df.rename(columns={"boundary_front_class": "boundary_front", "stage_chain_status": "chain_status"})
    needed = ["sample_id", "trajectory_id", "band", "boundary_front", "chain_status", "first_entry_index"]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in stage CSV: {missing}")

    for col in ["band", "boundary_front", "chain_status"]:
        df[col] = df[col].map(clean_text)
    df["state"] = df.apply(state_label, axis=1)
    df["sort_index"] = pd.to_numeric(df["first_entry_index"], errors="coerce")
    df = df.sort_values(["sample_id", "trajectory_id", "sort_index", "band"], kind="mergesort")
    return df


def build_transitions(stage: pd.DataFrame) -> pd.DataFrame:
    gcols = ["sample_id", "trajectory_id"]
    next_cols = {
        "state": "next_state",
        "band": "next_band",
        "boundary_front": "next_boundary_front",
        "chain_status": "next_chain_status",
    }
    work = stage.copy()
    for src, dst in next_cols.items():
        work[dst] = work.groupby(gcols, sort=False)[src].shift(-1)
    transitions = work.dropna(subset=["next_state"]).copy()

    table = (
        transitions.groupby(
            [
                "state",
                "next_state",
                "band",
                "boundary_front",
                "chain_status",
                "next_band",
                "next_boundary_front",
                "next_chain_status",
            ],
            dropna=False,
        )
        .size()
        .reset_index(name="count")
    )
    totals = table.groupby("state")["count"].transform("sum")
    table["probability"] = table["count"] / totals
    table = table[
        [
            "state",
            "next_state",
            "count",
            "probability",
            "band",
            "boundary_front",
            "chain_status",
            "next_band",
            "next_boundary_front",
            "next_chain_status",
        ]
    ].sort_values(["count", "state", "next_state"], ascending=[False, True, True])
    return table


def build_branching(transition_table: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for state, sub in transition_table.groupby("state", sort=False):
        counts = sub.set_index("next_state")["count"]
        top = counts.sort_values(ascending=False).head(1)
        total = int(counts.sum())
        rows.append(
            {
                "state": state,
                "total_outgoing": total,
                "out_degree": int(counts.size),
                "entropy": entropy_from_counts(counts),
                "top_next_state": top.index[0],
                "top_next_count": int(top.iloc[0]),
                "top_next_probability": float(top.iloc[0] / total),
            }
        )
    return pd.DataFrame(rows).sort_values(["entropy", "total_outgoing"], ascending=[False, False])


def build_convergence(transition_table: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for state, sub in transition_table.groupby("next_state", sort=False):
        counts = sub.groupby("state")["count"].sum()
        top = counts.sort_values(ascending=False).head(1)
        total = int(counts.sum())
        rows.append(
            {
                "state": state,
                "total_incoming": total,
                "in_degree": int(counts.size),
                "top_prev_state": top.index[0],
                "top_prev_count": int(top.iloc[0]),
                "top_prev_probability": float(top.iloc[0] / total),
            }
        )
    return pd.DataFrame(rows).sort_values(["total_incoming", "in_degree"], ascending=[False, False])


def build_band_summary(transition_table: pd.DataFrame, branching: pd.DataFrame) -> pd.DataFrame:
    entropy_map = branching.set_index("state")["entropy"].to_dict()
    rows = []
    for band, sub in transition_table.groupby("band", sort=False):
        by_next = sub.groupby("next_band")["count"].sum().sort_values(ascending=False)
        total = int(by_next.sum())
        states = sub["state"].drop_duplicates().tolist()
        state_entropies = pd.Series([entropy_map[s] for s in states if s in entropy_map], dtype=float)
        max_state = state_entropies.idxmax() if False else None
        max_entropy_state = ""
        if states:
            max_entropy_state = max(states, key=lambda s: entropy_map.get(s, -1.0))
        rows.append(
            {
                "band": band,
                "total_events": int(sub["count"].sum()),
                "outgoing_transitions": int(len(sub)),
                "dominant_next_band": by_next.index[0],
                "dominant_next_band_count": int(by_next.iloc[0]),
                "dominant_next_band_probability": float(by_next.iloc[0] / total),
                "mean_entropy_by_state": float(state_entropies.mean()) if len(state_entropies) else 0.0,
                "max_entropy_state": max_entropy_state,
            }
        )
    return pd.DataFrame(rows).sort_values("band", key=lambda s: s.map(sort_band_key))


def build_split_map(stage: pd.DataFrame, transition_table: pd.DataFrame) -> pd.DataFrame:
    events = pd.read_csv(EVENT_CSV)
    required = ["sample_id", "trajectory_id", "band", "residue_pair_mod32", "transition_k"]
    missing = [c for c in required if c not in events.columns]
    if missing:
        raise ValueError(f"Missing required columns in event CSV: {missing}")

    stage_lookup = stage[
        ["sample_id", "trajectory_id", "band", "boundary_front", "chain_status", "state"]
    ].drop_duplicates(["sample_id", "trajectory_id", "band"])
    joined = events.merge(stage_lookup, on=["sample_id", "trajectory_id", "band"], how="left")

    transition_lookup = transition_table.sort_values("count", ascending=False).drop_duplicates("state")[
        ["state", "next_state"]
    ]
    joined = joined.merge(transition_lookup, on="state", how="left")
    joined["boundary_front"] = joined["boundary_front"].map(clean_text)
    joined["residue_pair_mod32"] = joined["residue_pair_mod32"].map(clean_text)
    joined["transition_k"] = joined["transition_k"].map(clean_text)
    joined["next_state"] = joined["next_state"].map(clean_text)

    if "miss_event" in joined.columns:
        joined["split_group"] = np.where(joined["miss_event"].astype(str).isin(["1", "True", "true"]), "miss", "control")
    elif "near_behavior" in joined.columns:
        joined["split_group"] = np.where(joined["near_behavior"].astype(str).eq("miss"), "miss", "control")
    elif "group" in joined.columns:
        joined["split_group"] = np.where(joined["group"].astype(str).str.contains("miss", case=False, na=False), "miss", "control")
    else:
        joined["split_group"] = "other"

    known = joined["split_group"].isin(["miss", "control"])
    joined.loc[~known, "split_group"] = "other"

    rows = []
    key_cols = ["band", "boundary_front", "residue_pair_mod32", "transition_k"]
    for key, sub in joined.groupby(key_cols, dropna=False):
        counts = sub["split_group"].value_counts()
        next_counts = sub["next_state"].value_counts()
        miss_next = sub.loc[sub["split_group"].eq("miss"), "next_state"].value_counts()
        control_next = sub.loc[sub["split_group"].eq("control"), "next_state"].value_counts()
        rows.append(
            {
                "band": key[0],
                "boundary_front": key[1],
                "residue_pair_mod32": key[2],
                "transition_k": key[3],
                "miss_count": int(counts.get("miss", 0)),
                "control_count": int(counts.get("control", 0)),
                "other_count": int(counts.get("other", 0)),
                "next_state_distribution": distribution_string(next_counts),
                "dominant_miss_next_state": miss_next.index[0] if len(miss_next) else "",
                "dominant_control_next_state": control_next.index[0] if len(control_next) else "",
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["miss_count", "control_count", "band", "boundary_front"], ascending=[False, False, True, True]
    )


def plot_top_edges(transition_table: pd.DataFrame, path: Path, top_n: int = 28) -> None:
    top = transition_table.head(top_n).copy()
    nodes = sorted(set(top["state"]).union(top["next_state"]))
    node_band = {n: n.split("|", 1)[0] for n in nodes}
    bands = sorted(set(node_band.values()), key=sort_band_key)
    width, height = 1800, 1150
    margin_x, margin_y = 120, 130
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    title_font = font(30, True)
    label_font = font(15)
    small_font = font(13)

    draw.text((margin_x, 35), "Top empirical state transitions", fill="#1f2a33", font=title_font)
    band_x = {band: margin_x + i * ((width - 2 * margin_x) / max(1, len(bands) - 1)) for i, band in enumerate(bands)}
    grouped = {band: [n for n in nodes if node_band[n] == band] for band in bands}
    pos = {}
    for band, ns in grouped.items():
        ns = sorted(ns)
        step = (height - 2 * margin_y) / max(1, len(ns))
        for j, node in enumerate(ns):
            pos[node] = (band_x[band], margin_y + step * (j + 0.5))

    max_count = max(1, int(top["count"].max()))
    for r in top.sort_values("count").itertuples(index=False):
        x1, y1 = pos[r.state]
        x2, y2 = pos[r.next_state]
        if r.state == r.next_state:
            y2 -= 28
        w = 1 + int(7 * r.count / max_count)
        draw_arrow(draw, (x1 + 80, y1), (x2 - 80, y2), fill="#416a89", width=w)
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        draw.text((mx - 10, my - 16), str(int(r.count)), fill="#25313a", font=small_font)

    for node, (x, y) in pos.items():
        rx, ry = 88, 42
        draw.rounded_rectangle((x - rx, y - ry, x + rx, y + ry), radius=12, fill="#dcefff", outline="#324b5d", width=2)
        label = wrap_label(node, 18)
        lines = label.split("\n")
        total_h = sum(text_size(draw, line, label_font)[1] + 2 for line in lines)
        yy = y - total_h / 2
        for line in lines:
            tw, th = text_size(draw, line, label_font)
            draw.text((x - tw / 2, yy), line, fill="#15232c", font=label_font)
            yy += th + 2

    for band, x in band_x.items():
        tw, th = text_size(draw, band, label_font)
        draw.text((x - tw / 2, height - 55), band, fill="#26343d", font=label_font)
    img.save(path)


def plot_entropy(branching: pd.DataFrame, path: Path, top_n: int = 35) -> None:
    data = branching.sort_values(["entropy", "total_outgoing"], ascending=[False, False]).head(top_n).iloc[::-1]
    width = 1700
    row_h = 34
    left = 650
    right = 120
    top = 95
    height = top + row_h * len(data) + 90
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    title_font = font(30, True)
    label_font = font(15)
    small_font = font(13)
    draw.text((60, 35), "Branching entropy by state", fill="#1f2a33", font=title_font)
    max_e = max(float(data["entropy"].max()), 0.01)
    axis_w = width - left - right
    for tick in np.linspace(0, max_e, 5):
        x = left + axis_w * tick / max_e
        draw.line((x, top - 10, x, height - 70), fill="#e3e8ec", width=1)
        draw.text((x - 12, height - 58), f"{tick:.1f}", fill="#3d4a52", font=small_font)
    for i, r in enumerate(data.itertuples(index=False)):
        y = top + i * row_h
        draw.text((55, y + 5), r.state[:70], fill="#1b2933", font=label_font)
        bar_w = axis_w * float(r.entropy) / max_e
        draw.rounded_rectangle((left, y + 5, left + bar_w, y + row_h - 5), radius=5, fill="#70a66f")
        draw.text((left + bar_w + 8, y + 5), f"{float(r.entropy):.3f}", fill="#1f2a33", font=small_font)
    draw.text((left + axis_w / 2 - 40, height - 30), "Entropy (bits)", fill="#1f2a33", font=label_font)
    img.save(path)


def plot_band_heatmap(transition_table: pd.DataFrame, path: Path) -> None:
    matrix = transition_table.pivot_table(index="band", columns="next_band", values="count", aggfunc="sum", fill_value=0)
    bands = sorted(set(matrix.index).union(matrix.columns), key=sort_band_key)
    matrix = matrix.reindex(index=bands, columns=bands, fill_value=0)
    row_sums = matrix.sum(axis=1).replace(0, np.nan)
    share = matrix.div(row_sums, axis=0).fillna(0.0)

    cell = 110
    left = 170
    top = 145
    width = left + cell * len(bands) + 90
    height = top + cell * len(bands) + 90
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    title_font = font(30, True)
    label_font = font(16)
    small_font = font(13)
    draw.text((60, 35), "Band-to-band empirical flow heatmap", fill="#1f2a33", font=title_font)
    for j, band in enumerate(bands):
        x = left + j * cell
        draw.text((x + 5, top - 35), band, fill="#1f2a33", font=small_font)
    for i, band in enumerate(bands):
        y = top + i * cell
        draw.text((35, y + 42), band, fill="#1f2a33", font=label_font)
    max_val = max(float(share.values.max()), 0.01)
    for i in range(len(bands)):
        for j in range(len(bands)):
            p = float(share.iloc[i, j])
            count = int(matrix.iloc[i, j])
            color = blend_hex("#f7fbff", "#1166a5", p / max_val if max_val else 0)
            x0 = left + j * cell
            y0 = top + i * cell
            draw.rectangle((x0, y0, x0 + cell - 2, y0 + cell - 2), fill=color, outline="#d3dde5")
            if count:
                txt = f"{count}\n{p:.2f}"
                lines = txt.split("\n")
                yy = y0 + 34
                for line in lines:
                    tw, th = text_size(draw, line, small_font)
                    fill = "white" if p / max_val > 0.55 else "#17232c"
                    draw.text((x0 + cell / 2 - tw / 2, yy), line, fill=fill, font=small_font)
                    yy += th + 5
    draw.text((left + cell * len(bands) / 2 - 35, height - 45), "next_band", fill="#1f2a33", font=label_font)
    draw.text((35, top - 55), "band", fill="#1f2a33", font=label_font)
    img.save(path)


def write_report(
    stage: pd.DataFrame,
    transition_table: pd.DataFrame,
    branching: pd.DataFrame,
    convergence: pd.DataFrame,
    band_summary: pd.DataFrame,
    split_map: pd.DataFrame,
) -> None:
    top_edges = transition_table.head(12)
    top_entropy = branching.head(10)
    top_incoming = convergence.head(10)
    split_focus = split_map[(split_map["miss_count"] > 0) & (split_map["control_count"] > 0)].head(10)

    lines = []
    lines.append("# Empirical Flow Map Report")
    lines.append("")
    lines.append("finite-sample observational note: this report treats the rows as a finite empirical flow map on discrete states, not as a continuous physical vector field.")
    lines.append("")
    lines.append("## 1. Motivation")
    lines.append("")
    lines.append("The goal is to view the Collatz band material as movement across a finite state space. Instead of asking whether a single row is a miss or a control, the tables ask where a row sits, what state follows inside the same trajectory, and which states branch or receive flow in the observed sample.")
    lines.append("")
    lines.append("## 2. State definition")
    lines.append("")
    lines.append("The state used here is `band x boundary_front x chain_status`. In the source CSV this is implemented as `band`, `boundary_front_class`, and `stage_chain_status` from `band_stage_boundary_detail.csv`. The rendered label is `band|boundary_front|chain_status`.")
    lines.append("")
    lines.append("## 3. Transition construction")
    lines.append("")
    lines.append(f"Rows were sorted within `sample_id + trajectory_id` by `first_entry_index`, then adjacent rows were converted into `state_t -> state_t+1`. This produced {int(transition_table['count'].sum()):,} observed adjacent transitions across {transition_table['state'].nunique():,} source states and {transition_table['next_state'].nunique():,} destination states.")
    lines.append("")
    lines.append("## 4. Main flow map")
    lines.append("")
    lines.append("The largest edges are a compact downward band map. The most frequent transitions are:")
    lines.append("")
    lines.append("| state | next_state | count | probability |")
    lines.append("|---|---:|---:|---:|")
    for r in top_edges.itertuples(index=False):
        lines.append(f"| `{r.state}` | `{r.next_state}` | {int(r.count):,} | {float(r.probability):.3f} |")
    lines.append("")
    lines.append("The band summary keeps the same observation at a coarser scale:")
    lines.append("")
    lines.append("| band | total_events | dominant_next_band | probability | mean_entropy_by_state |")
    lines.append("|---|---:|---|---:|---:|")
    for r in band_summary.itertuples(index=False):
        lines.append(f"| {r.band} | {int(r.total_events):,} | {r.dominant_next_band} | {float(r.dominant_next_band_probability):.3f} | {float(r.mean_entropy_by_state):.3f} |")
    lines.append("")
    lines.append("## 5. Branching and convergence")
    lines.append("")
    lines.append("Branching is concentrated in a small number of observed states. Higher entropy means that the outgoing flow is less dominated by a single next state.")
    lines.append("")
    lines.append("| state | total_outgoing | out_degree | entropy | top_next_state | top_next_probability |")
    lines.append("|---|---:|---:|---:|---|---:|")
    for r in top_entropy.itertuples(index=False):
        lines.append(f"| `{r.state}` | {int(r.total_outgoing):,} | {int(r.out_degree)} | {float(r.entropy):.3f} | `{r.top_next_state}` | {float(r.top_next_probability):.3f} |")
    lines.append("")
    lines.append("Convergence highlights states that receive the largest incoming flow:")
    lines.append("")
    lines.append("| state | total_incoming | in_degree | top_prev_state | top_prev_probability |")
    lines.append("|---|---:|---:|---|---:|")
    for r in top_incoming.itertuples(index=False):
        lines.append(f"| `{r.state}` | {int(r.total_incoming):,} | {int(r.in_degree)} | `{r.top_prev_state}` | {float(r.top_prev_probability):.3f} |")
    lines.append("")
    lines.append("## 6. Miss/control split map")
    lines.append("")
    lines.append("The split map uses event-level rows from `miss_and_control_event_detail.csv`, grouped by `band + boundary_front + residue_pair_mod32 + transition_k`. The event rows were joined back to the stage state by `sample_id + trajectory_id + band`, then assigned the dominant observed next state for that stage state.")
    lines.append("")
    if len(split_focus):
        lines.append("| band | boundary_front | residue_pair_mod32 | transition_k | miss_count | control_count | dominant_miss_next_state | dominant_control_next_state |")
        lines.append("|---|---|---|---:|---:|---:|---|---|")
        for r in split_focus.itertuples(index=False):
            lines.append(f"| {r.band} | {r.boundary_front} | {r.residue_pair_mod32} | {r.transition_k} | {int(r.miss_count)} | {int(r.control_count)} | `{r.dominant_miss_next_state}` | `{r.dominant_control_next_state}` |")
    else:
        lines.append("No key cell in this event table contained both miss and control rows after the stage-state join. The CSV still records miss-only and control-only cells for inspection.")
    lines.append("")
    lines.append("## 7. Interpretation")
    lines.append("")
    lines.append("The finite map is consistent with a layered grammar: `32-63` is visible as a branching layer rather than only as a special class; `64-127` contributes many mixed upstream entries; `16-31` and `8-15` mostly look like avoid-channel passage in this state coding; and `4-7` appears as the main capture-side receiving layer. The miss rows are better read here as trajectories passing through a particular flow grammar than as isolated labels.")
    lines.append("")
    lines.append("## 8. Limits")
    lines.append("")
    lines.append("The map depends on the source CSV definitions and on the finite sample represented there. The miss/control split table also uses a dominant-next-state join from stage states, so it should be read as a coarse comparison map rather than an event-level causal mechanism.")
    lines.append("")
    lines.append("finite-sample observational note: the outputs are observation tables and figures for this dataset only; they do not assert proof, mechanism, generalization, counterexample, or any claim about the Collatz conjecture.")
    lines.append("")
    lines.append("## Output files")
    lines.append("")
    for name in [
        "transition_table.csv",
        "branching_table.csv",
        "convergence_table.csv",
        "band_flow_summary.csv",
        "miss_control_split_map.csv",
        "transition_graph_top_edges.png",
        "branching_entropy_by_state.png",
        "band_to_band_flow_heatmap.png",
    ]:
        lines.append(f"- `{name}`")
    lines.append("")
    lines.append("## Source files")
    lines.append("")
    lines.append(f"- `{STAGE_CSV}`")
    lines.append(f"- `{EVENT_CSV}`")

    (OUT / "empirical_flow_map_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    stage = prepare_stage_rows()
    transition_table = build_transitions(stage)
    branching = build_branching(transition_table)
    convergence = build_convergence(transition_table)
    band_summary = build_band_summary(transition_table, branching)
    split_map = build_split_map(stage, transition_table)

    transition_table.to_csv(OUT / "transition_table.csv", index=False, encoding="utf-8")
    branching.to_csv(OUT / "branching_table.csv", index=False, encoding="utf-8")
    convergence.to_csv(OUT / "convergence_table.csv", index=False, encoding="utf-8")
    band_summary.to_csv(OUT / "band_flow_summary.csv", index=False, encoding="utf-8")
    split_map.to_csv(OUT / "miss_control_split_map.csv", index=False, encoding="utf-8")

    plot_top_edges(transition_table, OUT / "transition_graph_top_edges.png")
    plot_entropy(branching, OUT / "branching_entropy_by_state.png")
    plot_band_heatmap(transition_table, OUT / "band_to_band_flow_heatmap.png")
    write_report(stage, transition_table, branching, convergence, band_summary, split_map)

    meta = {
        "stage_rows": int(len(stage)),
        "transition_events": int(transition_table["count"].sum()),
        "transition_edges": int(len(transition_table)),
        "states": int(transition_table["state"].nunique()),
        "split_rows": int(len(split_map)),
        "source_stage_csv": str(STAGE_CSV),
        "source_event_csv": str(EVENT_CSV),
        "output_dir": str(OUT),
    }
    (OUT / "run_summary.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
