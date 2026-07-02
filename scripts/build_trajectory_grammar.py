from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageColor, ImageDraw, ImageFont


ROOT = Path(r"C:\Users\yauki\Documents\Codex\2026-07-01\csv-collatz-state-band-boundary-front")
OUT = ROOT / "outputs" / "trajectory_grammar"
SRC_DIR = Path(r"C:\Users\yauki\Documents\design\collatz\boundary-front geometry\boundary-front-geometry\csv")
STAGE_CSV = SRC_DIR / "band_stage_boundary_detail.csv"
EVENT_CSV = SRC_DIR / "miss_and_control_event_detail.csv"

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


def state_label(row: pd.Series) -> str:
    return f"{clean_text(row['band'])}|{clean_text(row['boundary_front'])}|{clean_text(row['chain_status'])}"


def split_route(route: str) -> list[str]:
    if not route:
        return []
    return [part for part in route.split(" -> ") if part]


def compress_states(states: list[str]) -> list[str]:
    out: list[str] = []
    for state in states:
        if not out or out[-1] != state:
            out.append(state)
    return out


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
        tail = int(counts.sort_values(ascending=False).iloc[limit:].sum())
        parts.append(f"other_states:{tail} ({tail / total:.3f})")
    return "; ".join(parts)


def sort_band_key(band: str) -> tuple[int, str]:
    if band in BAND_ORDER:
        return (BAND_ORDER.index(band), band)
    return (len(BAND_ORDER), band)


def band_from_state(state: str) -> str:
    return state.split("|", 1)[0] if state else "NA"


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


def wrap_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "."


def blend_hex(c1: str, c2: str, t: float) -> tuple[int, int, int]:
    a = np.array(ImageColor.getrgb(c1), dtype=float)
    b = np.array(ImageColor.getrgb(c2), dtype=float)
    return tuple(np.round(a * (1 - t) + b * t).astype(int))


def draw_arrow(draw: ImageDraw.ImageDraw, p1: tuple[float, float], p2: tuple[float, float], fill, width: int = 2) -> None:
    x1, y1 = p1
    x2, y2 = p2
    draw.line((x1, y1, x2, y2), fill=fill, width=width)
    angle = math.atan2(y2 - y1, x2 - x1)
    head = 10 + width
    spread = 0.42
    pts = [
        (x2, y2),
        (x2 + head * math.cos(angle + math.pi - spread), y2 + head * math.sin(angle + math.pi - spread)),
        (x2 + head * math.cos(angle + math.pi + spread), y2 + head * math.sin(angle + math.pi + spread)),
    ]
    draw.polygon(pts, fill=fill)


def prepare_stage_rows() -> pd.DataFrame:
    df = pd.read_csv(STAGE_CSV)
    df = df.rename(columns={"boundary_front_class": "boundary_front", "stage_chain_status": "chain_status"})
    required = ["sample_id", "trajectory_id", "band", "boundary_front", "chain_status", "first_entry_index"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in stage CSV: {missing}")
    for col in ["band", "boundary_front", "chain_status"]:
        df[col] = df[col].map(clean_text)
    df["state_label"] = df.apply(state_label, axis=1)
    df["sort_index"] = pd.to_numeric(df["first_entry_index"], errors="coerce")
    return df.sort_values(["sample_id", "trajectory_id", "sort_index", "band"], kind="mergesort")


def event_counts_by_trajectory() -> pd.DataFrame:
    if not EVENT_CSV.exists():
        return pd.DataFrame(columns=["sample_id", "trajectory_id", "miss_count", "control_count"])
    events = pd.read_csv(EVENT_CSV)
    required = ["sample_id", "trajectory_id"]
    missing = [c for c in required if c not in events.columns]
    if missing:
        raise ValueError(f"Missing required columns in event CSV: {missing}")

    if "miss_event" in events.columns:
        miss_mask = events["miss_event"].astype(str).isin(["1", "True", "true"])
    elif "near_behavior" in events.columns:
        miss_mask = events["near_behavior"].astype(str).eq("miss")
    else:
        miss_mask = events.get("group", pd.Series([""] * len(events))).astype(str).str.contains("miss", case=False, na=False)

    if "group" in events.columns:
        control_mask = events["group"].astype(str).str.contains("control", case=False, na=False) & ~miss_mask
    else:
        control_mask = ~miss_mask

    events = events.assign(_miss=miss_mask.astype(int), _control=control_mask.astype(int))
    return (
        events.groupby(["sample_id", "trajectory_id"], dropna=False)[["_miss", "_control"]]
        .sum()
        .rename(columns={"_miss": "miss_count", "_control": "control_count"})
        .reset_index()
    )


def build_trajectory_routes(stage: pd.DataFrame) -> pd.DataFrame:
    labels = event_counts_by_trajectory()
    rows = []
    for (sample_id, trajectory_id), sub in stage.groupby(["sample_id", "trajectory_id"], sort=False):
        states = sub["state_label"].tolist()
        compressed = compress_states(states)
        bands = [band_from_state(s) for s in compressed]
        ordered_bands = sorted(set(bands), key=sort_band_key)
        rows.append(
            {
                "sample_id": sample_id,
                "trajectory_id": trajectory_id,
                "n_stages": len(states),
                "full_route": " -> ".join(states),
                "compressed_route": " -> ".join(compressed),
                "start_state": compressed[0] if compressed else "",
                "end_state": compressed[-1] if compressed else "",
                "min_band": ordered_bands[0] if ordered_bands else "",
                "max_band": ordered_bands[-1] if ordered_bands else "",
            }
        )
    routes = pd.DataFrame(rows)
    routes = routes.merge(labels, on=["sample_id", "trajectory_id"], how="left")
    routes[["miss_count", "control_count"]] = routes[["miss_count", "control_count"]].fillna(0).astype(int)
    routes["contains_miss"] = routes["miss_count"] > 0
    routes["contains_control"] = routes["control_count"] > 0
    return routes[
        [
            "sample_id",
            "trajectory_id",
            "n_stages",
            "full_route",
            "compressed_route",
            "start_state",
            "end_state",
            "contains_miss",
            "contains_control",
            "miss_count",
            "control_count",
            "min_band",
            "max_band",
        ]
    ]


def route_frequency(routes: pd.DataFrame) -> pd.DataFrame:
    grouped = routes.groupby("compressed_route", sort=False)
    rows = []
    total = len(routes)
    for route, sub in grouped:
        states = split_route(route)
        miss_count = int(sub["miss_count"].sum())
        control_count = int(sub["control_count"].sum())
        other_count = int((~sub["contains_miss"] & ~sub["contains_control"]).sum())
        denom = miss_count + control_count
        rows.append(
            {
                "compressed_route": route,
                "count": int(len(sub)),
                "probability": float(len(sub) / total) if total else 0.0,
                "n_stages": len(states),
                "start_state": states[0] if states else "",
                "end_state": states[-1] if states else "",
                "miss_count": miss_count,
                "control_count": control_count,
                "other_count": other_count,
                "miss_rate": float(miss_count / denom) if denom else 0.0,
            }
        )
    return pd.DataFrame(rows).sort_values(["count", "miss_count", "control_count"], ascending=[False, False, False])


def filtered_route_table(routes: pd.DataFrame, route_freq: pd.DataFrame, label: str) -> pd.DataFrame:
    if label == "miss":
        subset = routes[routes["contains_miss"]]
        prob_col = "probability_within_miss_routes"
    else:
        subset = routes[routes["contains_control"]]
        prob_col = "probability_within_control_routes"
    counts = subset["compressed_route"].value_counts()
    total = int(counts.sum())
    base = route_freq.set_index("compressed_route")
    rows = []
    for route, count in counts.items():
        r = base.loc[route]
        rows.append(
            {
                "compressed_route": route,
                "count": int(count),
                prob_col: float(count / total) if total else 0.0,
                "miss_count": int(r["miss_count"]),
                "control_count": int(r["control_count"]),
                "n_stages": int(r["n_stages"]),
                "start_state": r["start_state"],
                "end_state": r["end_state"],
            }
        )
    return pd.DataFrame(rows).sort_values(["count", "miss_count", "control_count"], ascending=[False, False, False])


def build_prefix_table(routes: pd.DataFrame) -> pd.DataFrame:
    rows = []
    expanded = [(split_route(r.compressed_route), r) for r in routes.itertuples(index=False)]
    max_len = max((len(states) for states, _ in expanded), default=0)
    for length in range(1, max_len):
        prefix_map: dict[tuple[str, ...], list[tuple[str | None, object]]] = {}
        for states, row in expanded:
            if len(states) <= length:
                continue
            prefix = tuple(states[:length])
            next_state = states[length]
            prefix_map.setdefault(prefix, []).append((next_state, row))
        for prefix, items in prefix_map.items():
            next_counts = pd.Series([item[0] for item in items]).value_counts()
            miss_count = int(sum(item[1].miss_count for item in items))
            control_count = int(sum(item[1].control_count for item in items))
            denom = miss_count + control_count
            top = next_counts.head(1)
            rows.append(
                {
                    "prefix": " -> ".join(prefix),
                    "prefix_length": length,
                    "total_count": len(items),
                    "next_state_count": int(next_counts.sum()),
                    "next_state_distribution": distribution_string(next_counts),
                    "out_degree": int(len(next_counts)),
                    "entropy": entropy_from_counts(next_counts),
                    "top_next_state": top.index[0],
                    "top_next_probability": float(top.iloc[0] / next_counts.sum()),
                    "miss_count": miss_count,
                    "control_count": control_count,
                    "miss_rate": float(miss_count / denom) if denom else 0.0,
                }
            )
    return pd.DataFrame(rows).sort_values(["entropy", "total_count"], ascending=[False, False])


def build_suffix_table(routes: pd.DataFrame) -> pd.DataFrame:
    rows = []
    expanded = [(split_route(r.compressed_route), r) for r in routes.itertuples(index=False)]
    max_len = max((len(states) for states, _ in expanded), default=0)
    for length in range(1, max_len):
        suffix_map: dict[tuple[str, ...], list[tuple[str | None, object]]] = {}
        for states, row in expanded:
            if len(states) <= length:
                continue
            suffix = tuple(states[-length:])
            prev_state = states[-length - 1]
            suffix_map.setdefault(suffix, []).append((prev_state, row))
        for suffix, items in suffix_map.items():
            prev_counts = pd.Series([item[0] for item in items]).value_counts()
            miss_count = int(sum(item[1].miss_count for item in items))
            control_count = int(sum(item[1].control_count for item in items))
            denom = miss_count + control_count
            top = prev_counts.head(1)
            rows.append(
                {
                    "suffix": " -> ".join(suffix),
                    "suffix_length": length,
                    "total_count": len(items),
                    "prev_state_count": int(prev_counts.sum()),
                    "prev_state_distribution": distribution_string(prev_counts),
                    "in_degree": int(len(prev_counts)),
                    "entropy": entropy_from_counts(prev_counts),
                    "top_prev_state": top.index[0],
                    "top_prev_probability": float(top.iloc[0] / prev_counts.sum()),
                    "miss_count": miss_count,
                    "control_count": control_count,
                    "miss_rate": float(miss_count / denom) if denom else 0.0,
                }
            )
    return pd.DataFrame(rows).sort_values(["entropy", "total_count"], ascending=[False, False])


def route_has_adjacent_bands(states: list[str], first: str, second: str, status: str | None = None) -> bool:
    for a, b in zip(states, states[1:]):
        if band_from_state(a) == first and band_from_state(b) == second:
            if status is None or (a.endswith(f"|{status}") and b.endswith(f"|{status}")):
                return True
    return False


def build_route_families(routes: pd.DataFrame) -> pd.DataFrame:
    route_rows = []
    route_freq = route_frequency(routes)
    next_after_32 = set()
    next_after_64_to_32 = set()
    for route in route_freq["compressed_route"]:
        states = split_route(route)
        for a, b in zip(states, states[1:]):
            if band_from_state(a) == "32-63":
                next_after_32.add(b)
            if band_from_state(a) == "64-127" and band_from_state(b) == "32-63":
                next_after_64_to_32.add(b)

    def matching_families(states: list[str]) -> list[tuple[str, str]]:
        route = " -> ".join(states)
        families = []
        if states and "4-7" in band_from_state(states[-1]):
            families.append(("capture_sink_4_7", "end_state contains 4-7"))
        if route_has_adjacent_bands(states, "16-31", "8-15", "avoid"):
            families.append(("avoid_channel", "16-31 avoid followed by 8-15 avoid"))
        if any(band_from_state(s) == "32-63" for s in states) and len(next_after_32) > 1:
            families.append(("branch_at_32_63", "32-63 appears in a route with multiple observed next-state series"))
        if any(band_from_state(s) == "64-127" for s in states) and len(next_after_64_to_32) > 1:
            families.append(("upstream_mixed_64_127", "64-127 appears upstream of multiple 32-63 states"))
        if len(states) <= 3 and all("|lower_edge_front|" in s for s in states) and any(s.endswith("|caught") for s in states):
            families.append(("short_lower_capture", "short lower-edge route ending or passing through caught"))
        if any("|near_exit_front|avoid" in s for s in states):
            families.append(("near_front_avoid_route", "route contains near_exit_front + avoid"))
        return families

    for r in route_freq.itertuples(index=False):
        states = split_route(r.compressed_route)
        for family, notes in matching_families(states):
            route_rows.append(
                {
                    "route_family": family,
                    "compressed_route": r.compressed_route,
                    "trajectory_count": int(r.count),
                    "miss_count": int(r.miss_count),
                    "control_count": int(r.control_count),
                    "notes": notes,
                }
            )
    family_route = pd.DataFrame(route_rows)
    if family_route.empty:
        return pd.DataFrame(
            columns=[
                "route_family",
                "route_count",
                "trajectory_count",
                "miss_count",
                "control_count",
                "miss_rate",
                "representative_route",
                "notes",
            ]
        )

    rows = []
    for family, sub in family_route.groupby("route_family"):
        miss_count = int(sub["miss_count"].sum())
        control_count = int(sub["control_count"].sum())
        denom = miss_count + control_count
        top = sub.sort_values("trajectory_count", ascending=False).iloc[0]
        rows.append(
            {
                "route_family": family,
                "route_count": int(sub["compressed_route"].nunique()),
                "trajectory_count": int(sub["trajectory_count"].sum()),
                "miss_count": miss_count,
                "control_count": control_count,
                "miss_rate": float(miss_count / denom) if denom else 0.0,
                "representative_route": top["compressed_route"],
                "notes": top["notes"],
            }
        )
    return pd.DataFrame(rows).sort_values(["trajectory_count", "route_count"], ascending=[False, False])


def plot_bar(data: pd.DataFrame, label_col: str, value_col: str, title: str, path: Path, top_n: int = 20) -> None:
    data = data.head(top_n).iloc[::-1]
    width = 1800
    row_h = 42
    left = 880
    right = 120
    top = 100
    height = top + row_h * max(1, len(data)) + 90
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    title_font = font(30, True)
    label_font = font(14)
    small_font = font(13)
    draw.text((60, 35), title, fill="#1f2a33", font=title_font)
    max_v = max(float(data[value_col].max()) if len(data) else 0, 0.01)
    axis_w = width - left - right
    for i, r in enumerate(data.itertuples(index=False)):
        y = top + i * row_h
        label = wrap_text(str(getattr(r, label_col)), 110)
        draw.text((55, y + 8), label, fill="#1b2933", font=label_font)
        value = float(getattr(r, value_col))
        bar_w = axis_w * value / max_v
        draw.rounded_rectangle((left, y + 7, left + bar_w, y + row_h - 7), radius=5, fill="#5d89b3")
        draw.text((left + bar_w + 8, y + 8), f"{value:g}", fill="#1f2a33", font=small_font)
    img.save(path)


def plot_miss_control_bar(miss_table: pd.DataFrame, control_table: pd.DataFrame, path: Path) -> None:
    miss = miss_table.head(12).copy()
    miss["group"] = "miss"
    control = control_table.head(12).copy()
    control["group"] = "control"
    data = pd.concat([miss, control], ignore_index=True)
    width, height = 1900, 1150
    left, top, row_h = 900, 100, 38
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    title_font = font(30, True)
    label_font = font(13)
    small_font = font(12)
    draw.text((60, 35), "Miss/control route top comparison", fill="#1f2a33", font=title_font)
    max_v = max(float(data["count"].max()) if len(data) else 0, 1)
    for i, r in enumerate(data.itertuples(index=False)):
        y = top + i * row_h
        color = "#b7605c" if r.group == "miss" else "#5d89b3"
        prefix = "M " if r.group == "miss" else "C "
        draw.text((55, y + 6), prefix + wrap_text(r.compressed_route, 108), fill="#1b2933", font=label_font)
        bar_w = (width - left - 140) * int(r.count) / max_v
        draw.rounded_rectangle((left, y + 6, left + bar_w, y + row_h - 6), radius=5, fill=color)
        draw.text((left + bar_w + 8, y + 6), str(int(r.count)), fill="#1f2a33", font=small_font)
    img.save(path)


def plot_route_tree(prefix_table: pd.DataFrame, path: Path, top_n: int = 28) -> None:
    top = prefix_table.sort_values(["total_count", "entropy"], ascending=[False, False]).head(top_n)
    edges: dict[tuple[str, str], int] = {}
    nodes: set[str] = set()
    for r in top.itertuples(index=False):
        prefix_states = split_route(r.prefix)
        if not prefix_states:
            continue
        parent = prefix_states[-1]
        dist = str(r.next_state_distribution).split("; ")
        for part in dist[:4]:
            if not part:
                continue
            state = part.split(":", 1)[0]
            count_text = part.split(":", 1)[1].split(" ", 1)[0] if ":" in part else "0"
            try:
                count = int(count_text)
            except ValueError:
                count = 0
            edges[(parent, state)] = edges.get((parent, state), 0) + count
            nodes.update([parent, state])

    width, height = 1900, 1200
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    title_font = font(30, True)
    label_font = font(13)
    small_font = font(12)
    draw.text((60, 35), "Route tree from top prefixes", fill="#1f2a33", font=title_font)
    bands = sorted(set(band_from_state(n) for n in nodes), key=sort_band_key, reverse=True)
    grouped = {band: sorted([n for n in nodes if band_from_state(n) == band]) for band in bands}
    x_for = {band: 140 + i * ((width - 280) / max(1, len(bands) - 1)) for i, band in enumerate(bands)}
    pos: dict[str, tuple[float, float]] = {}
    for band, ns in grouped.items():
        step = (height - 190) / max(1, len(ns))
        for j, node in enumerate(ns):
            pos[node] = (x_for[band], 120 + step * (j + 0.5))
    max_count = max(edges.values(), default=1)
    for (a, b), count in sorted(edges.items(), key=lambda kv: kv[1]):
        if a not in pos or b not in pos:
            continue
        x1, y1 = pos[a]
        x2, y2 = pos[b]
        draw_arrow(draw, (x1 + 82, y1), (x2 - 82, y2), fill="#496f8d", width=1 + int(6 * count / max_count))
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        draw.text((mx, my - 14), str(count), fill="#26343d", font=small_font)
    for node, (x, y) in pos.items():
        draw.rounded_rectangle((x - 86, y - 34, x + 86, y + 34), radius=10, fill="#e7f2fa", outline="#30495a", width=1)
        lines = node.split("|")
        yy = y - 24
        for line in lines:
            line = wrap_text(line, 18)
            tw, th = text_size(draw, line, label_font)
            draw.text((x - tw / 2, yy), line, fill="#15232c", font=label_font)
            yy += th + 1
    img.save(path)


def write_report(
    routes: pd.DataFrame,
    route_freq: pd.DataFrame,
    miss_routes: pd.DataFrame,
    control_routes: pd.DataFrame,
    prefix_table: pd.DataFrame,
    suffix_table: pd.DataFrame,
    family_summary: pd.DataFrame,
) -> None:
    lines = []
    lines.append("# Trajectory Grammar Report")
    lines.append("")
    lines.append("finite-sample observational note: this report treats trajectory routes as a finite observational route dictionary over discrete states.")
    lines.append("")
    lines.append("## 1. Motivation")
    lines.append("")
    lines.append("The previous map counted local `state -> next_state` moves. This pass keeps each trajectory as an ordered route, so the main object is the state sequence itself: where a trajectory starts, which corridor it passes through, where it branches, and which suffixes recur.")
    lines.append("")
    lines.append("## 2. Route construction")
    lines.append("")
    lines.append(f"`band_stage_boundary_detail.csv` was sorted by `sample_id + trajectory_id + first_entry_index`. The state label is `band|boundary_front_class|stage_chain_status`. Consecutive repeated states were compressed, while the full uncompressed route was also retained. The resulting table contains {len(routes):,} trajectories and {route_freq['compressed_route'].nunique():,} distinct compressed routes.")
    lines.append("")
    lines.append("## 3. Most frequent routes")
    lines.append("")
    lines.append("| compressed_route | count | probability | miss_count | control_count |")
    lines.append("|---|---:|---:|---:|---:|")
    for r in route_freq.head(10).itertuples(index=False):
        lines.append(f"| `{r.compressed_route}` | {int(r.count):,} | {float(r.probability):.3f} | {int(r.miss_count)} | {int(r.control_count)} |")
    lines.append("")
    lines.append("## 4. Miss-bearing routes")
    lines.append("")
    lines.append("| compressed_route | count | probability_within_miss_routes | miss_count | control_count |")
    lines.append("|---|---:|---:|---:|---:|")
    for r in miss_routes.head(10).itertuples(index=False):
        lines.append(f"| `{r.compressed_route}` | {int(r.count):,} | {float(r.probability_within_miss_routes):.3f} | {int(r.miss_count)} | {int(r.control_count)} |")
    lines.append("")
    lines.append("## 5. Control-bearing routes")
    lines.append("")
    lines.append("| compressed_route | count | probability_within_control_routes | miss_count | control_count |")
    lines.append("|---|---:|---:|---:|---:|")
    for r in control_routes.head(10).itertuples(index=False):
        lines.append(f"| `{r.compressed_route}` | {int(r.count):,} | {float(r.probability_within_control_routes):.3f} | {int(r.miss_count)} | {int(r.control_count)} |")
    lines.append("")
    lines.append("## 6. Prefix branching")
    lines.append("")
    lines.append("Prefixes show where the same initial route begins to split into different next states.")
    lines.append("")
    lines.append("| prefix | total_count | out_degree | entropy | top_next_state | top_next_probability |")
    lines.append("|---|---:|---:|---:|---|---:|")
    for r in prefix_table.head(10).itertuples(index=False):
        lines.append(f"| `{r.prefix}` | {int(r.total_count):,} | {int(r.out_degree)} | {float(r.entropy):.3f} | `{r.top_next_state}` | {float(r.top_next_probability):.3f} |")
    lines.append("")
    lines.append("## 7. Suffix convergence")
    lines.append("")
    lines.append("Suffixes show where different earlier routes converge into the same ending grammar.")
    lines.append("")
    lines.append("| suffix | total_count | in_degree | entropy | top_prev_state | top_prev_probability |")
    lines.append("|---|---:|---:|---:|---|---:|")
    for r in suffix_table.head(10).itertuples(index=False):
        lines.append(f"| `{r.suffix}` | {int(r.total_count):,} | {int(r.in_degree)} | {float(r.entropy):.3f} | `{r.top_prev_state}` | {float(r.top_prev_probability):.3f} |")
    lines.append("")
    lines.append("## 8. Route families")
    lines.append("")
    lines.append("| route_family | route_count | trajectory_count | miss_count | control_count | miss_rate | notes |")
    lines.append("|---|---:|---:|---:|---:|---:|---|")
    for r in family_summary.itertuples(index=False):
        lines.append(f"| {r.route_family} | {int(r.route_count)} | {int(r.trajectory_count):,} | {int(r.miss_count)} | {int(r.control_count)} | {float(r.miss_rate):.3f} | {r.notes} |")
    lines.append("")
    lines.append("## 9. Interpretation")
    lines.append("")
    lines.append("The route dictionary makes the band sequence more legible than isolated state counts. The common grammar runs downward through `32-63`, `16-31`, `8-15`, and into `4-7`, while several high-entropy prefixes show that `32-63` acts more like a branching intersection than a single special point. The `16-31 -> 8-15` avoid passage appears as a repeated channel, and many endings collect into a `4-7` capture-side suffix. Miss-bearing rows are therefore easier to read as traveling on a route grammar than as a single coordinate condition.")
    lines.append("")
    lines.append("## 10. Limits")
    lines.append("")
    lines.append("The route grammar is tied to the source CSV definitions and to the finite sample represented by those rows. The miss/control labels are attached at the trajectory level from `miss_and_control_event_detail.csv`, so they indicate which routes carry those observed event labels rather than explaining why they occur.")
    lines.append("")
    lines.append("finite-sample observational note: these outputs are route dictionaries, split tables, and figures for this dataset only; they do not assert proof, mechanism, generalization, or any claim about the Collatz conjecture.")
    lines.append("")
    lines.append("## Output files")
    lines.append("")
    for name in [
        "trajectory_routes.csv",
        "route_frequency_table.csv",
        "miss_route_table.csv",
        "control_route_table.csv",
        "route_prefix_split_table.csv",
        "route_suffix_convergence_table.csv",
        "route_family_summary.csv",
        "top_route_bar.png",
        "miss_vs_control_route_bar.png",
        "prefix_branching_entropy.png",
        "suffix_convergence_entropy.png",
        "route_tree_top_prefixes.png",
    ]:
        lines.append(f"- `{name}`")
    lines.append("")
    lines.append("## Source files")
    lines.append("")
    lines.append(f"- `{STAGE_CSV}`")
    lines.append(f"- `{EVENT_CSV}`")
    (OUT / "trajectory_grammar_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    stage = prepare_stage_rows()
    routes = build_trajectory_routes(stage)
    route_freq = route_frequency(routes)
    miss_routes = filtered_route_table(routes, route_freq, "miss")
    control_routes = filtered_route_table(routes, route_freq, "control")
    prefix_table = build_prefix_table(routes)
    suffix_table = build_suffix_table(routes)
    family_summary = build_route_families(routes)

    routes.to_csv(OUT / "trajectory_routes.csv", index=False, encoding="utf-8")
    route_freq.to_csv(OUT / "route_frequency_table.csv", index=False, encoding="utf-8")
    miss_routes.to_csv(OUT / "miss_route_table.csv", index=False, encoding="utf-8")
    control_routes.to_csv(OUT / "control_route_table.csv", index=False, encoding="utf-8")
    prefix_table.to_csv(OUT / "route_prefix_split_table.csv", index=False, encoding="utf-8")
    suffix_table.to_csv(OUT / "route_suffix_convergence_table.csv", index=False, encoding="utf-8")
    family_summary.to_csv(OUT / "route_family_summary.csv", index=False, encoding="utf-8")

    plot_bar(route_freq, "compressed_route", "count", "Top compressed routes", OUT / "top_route_bar.png")
    plot_miss_control_bar(miss_routes, control_routes, OUT / "miss_vs_control_route_bar.png")
    plot_bar(prefix_table, "prefix", "entropy", "Top prefix branching entropy", OUT / "prefix_branching_entropy.png")
    plot_bar(suffix_table, "suffix", "entropy", "Top suffix convergence entropy", OUT / "suffix_convergence_entropy.png")
    plot_route_tree(prefix_table, OUT / "route_tree_top_prefixes.png")
    write_report(routes, route_freq, miss_routes, control_routes, prefix_table, suffix_table, family_summary)

    meta = {
        "stage_rows": int(len(stage)),
        "trajectories": int(len(routes)),
        "distinct_compressed_routes": int(route_freq["compressed_route"].nunique()),
        "miss_bearing_trajectories": int(routes["contains_miss"].sum()),
        "control_bearing_trajectories": int(routes["contains_control"].sum()),
        "prefix_rows": int(len(prefix_table)),
        "suffix_rows": int(len(suffix_table)),
        "output_dir": str(OUT),
        "source_stage_csv": str(STAGE_CSV),
        "source_event_csv": str(EVENT_CSV),
    }
    (OUT / "run_summary.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
