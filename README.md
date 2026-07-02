# Boundary-front geometry and finite trajectory atlas

An observational research note. This is **not** a paper, **not** a proof, and
**not** a new chapter of the Waiting Hall material. It records a finite-sample
exploration: what a set of audits looked at, what was seen, and what was
explicitly *not* seen. Every statement is about a specific finite event/stage
table. Words like `control`, `miss`, `front`, and `flow` are descriptive names
for rows and states in that table — not causal, experimental, or mechanistic
terms.

We do not prove the Collatz conjecture. We construct a finite-sample coordinate
atlas of observed accelerated trajectories.

---

## 1. What this note is — and its relation to `collatz-waiting-hall`

This note is a **derivative** of the Waiting Hall work, not the same chapter, and
it should not be merged with it.

- **`collatz-waiting-hall`** asked a *miss-selector / signal-vs-background*
  question: which coordinates isolate the observed miss events inside the
  waiting hall, ending in the finite-sample selector identity
  `P_pos ∩ S_shape = M`.
- **This note** takes the leftover of that identity — the 47 non-miss rows
  `S_shape \ M` — and widens the lens into a *boundary-front geometry /
  trajectory grammar / empirical flow atlas*. The object of study is no longer a
  single selector cell but the shape of trajectories as they descend across
  bands.

In one line: the earlier work was about **separating a signal**; this note is
about **drawing an atlas** of where the observed rows travel. The claim strength
is not raised — it moves from *classification* to a *finite trajectory atlas*,
nothing more.

---

## 2. Main results at the point of this write-up

Stated as observations. Interpretation is held to §4.

The previous chapter left off with `P_pos ∩ S_shape = M`, where `S_shape` (rows
whose `residue_pair_mod32` sits in the miss-event residue support) contains all
**228** miss events **and 47** non-miss rows (`S_shape \ M`). Today's core
results concern those 47 controls and, for contrast, the **120** depth-3 miss
rows.

**2.1 The 47 controls are structured, not diffuse.** They occupy exactly three
exit distances (`35:27, 36:12, 37:8`) and a narrow `remaining_K_before` range
(`99:27, 100:10, 101:7, 164:2, 165:1`), are all `drift`-labelled, and all have
`max_avoidance_depth = 2`. Their residue-shape cells line up with miss-front
cells shifted in position (e.g. control `3->30` at `exit_distance 35` matches a
miss `3->30` at `exit_distance 3`, same `transition_k = 5`).

**2.2 Controls and depth-3 miss rows share a coarse downstream suffix.** Both
run `16-31:avoid > 8-15:avoid` and are then captured at `4-7`. Depth-3 miss rows
carry one earlier band in the max-depth run (`32-63 > 16-31 > 8-15`); the
controls' max-depth run is `16-31 > 8-15`. The controls are **not** missing the
`32-63` stage — they have a `32-63` event, classified differently.

**2.3 At `32-63`, three descriptors must be kept apart — only two separate the groups.**
For controls (47) vs depth-3 miss rows (120) at the `32-63` stage:

| `32-63` descriptor | controls (47) | depth-3 miss (120) | separates here? |
|---|---|---|:---:|
| local event classification | `avoid_then_caught` | `avoid_then_caught` | no |
| chain status | `avoid_then_caught` | `avoid` | yes |
| boundary-front position | lower edge, mostly `R=32 -> 29` (44/47) | higher front, mostly `R=35/36/37 -> 31/30` | yes |

Local event classification is identical for both, so it does not separate them.
Chain status and boundary-front position do.

**2.4 A boundary-front coordinate separates the two groups in this table.**
Controls have `last_before_exit_distance ∈ {0,1}` (47/47); depth-3 miss rows have
`last_before_exit_distance ∈ {2,3,4,5,7,8}` (120/120). This coordinate is a
boundary-aligned re-expression of the final band position,
`last_before_exit_distance = last_before_R − band_lower`, so it is useful as a
**display** coordinate for the front but is **not independent** of
`last_before_R`.

**2.5 Downstream reconvergence is partial, not immediate.** The first `16-31`
shapes overlap only partly and their prefix distributions stay visibly
different. Both groups end at `4-7` capture, but with different final-status
mixes (controls `caught` 45/47; depth-3 miss `avoid_then_caught` 115/120).
Pairing quality confirms this: same `8-15` entry shape 47/47 and same `4-7`
entry shape 47/47, but same `16-31` entry shape only 2/47 and same selected
shape 1/47.

**2.6 Boundary-front structure appears across multiple bands.** Re-run as a
geometry audit, the lower-edge / near-exit / deeper front classes are present in
every band with enough rows, including bands with no observed miss events.
Miss-supported residue shapes appear only in `32-63` (159), `64-127` (97), and
`128-255` (19). The finite-table summary of how cleanly each coordinate groups
chain status was higher for boundary-front position than for local event
classification **only** in the `32-63` band:

| band | rows | miss rows | front classes present | front groups chain status better than local class? |
|---|---:|---:|---|:---:|
| 4-7 | 2581 | 0 | lower | no (0.603 vs 1.000) |
| 8-15 | 2744 | 0 | lower, near | no (0.980 vs 0.983) |
| 16-31 | 2744 | 0 | lower, near, deeper | no (0.870 vs 0.870) |
| 32-63 | 2489 | 159 | lower, near | **yes (0.991 vs 0.885)** |
| 64-127 | 1754 | 53 | lower, near | no (0.941 vs 0.984) |
| 128-255 | 241 | 16 | lower, near | no (0.714 vs 1.000) |
| 256-511 | 3 | 0 | lower | no (0.667 vs 1.000) |

(The parenthetical pairs are finite-table grouping-purity summaries for chain
status: boundary-front vs local event classification. They summarize this table
only.)

**Failed hypotheses (tested, not supported in this finite table):** shape alone
is miss-only (false; the 47 controls are the leakage); shape + `transition_k` is
miss-only (false; the same 47 remain); `transition_k` alone separates
controls from miss (false); local event classification explains the `32-63`
split (false; both `avoid_then_caught`); controls lack a `32-63` stage (false;
present, classified differently); the two groups reconverge immediately after
`16-31` (not supported); controls are depth-2 miss rows shifted upward (not
supported); `32-63` is unique (not supported — the contrast is *clearest* there,
not exclusive to it).

---

## 3. Subsequent progress: from classification to a finite trajectory atlas

The follow-up audits stopped asking "is this row a miss?" and started drawing the
trajectories as routes and numeric paths across the same finite table. This is a
change of viewpoint, not a stronger claim.

**3.1 Trajectory grammar — routes as a finite dictionary.** Treating each
trajectory as an ordered route over states `band|boundary_front|chain_status`
(consecutive repeats compressed) gives **2,750 trajectories** and **144 distinct
compressed routes**. The most frequent route (`64-127 … -> 4-7|…|caught`) covers
1,081 trajectories (prob 0.393). Route families summarize the shape:
`capture_sink_4_7` (105 routes, 2,581 trajectories), `branch_at_32_63` (114
routes, 2,489 trajectories), `avoid_channel` (85, 2,360),
`near_front_avoid_route` (107, 2,206), `upstream_mixed_64_127` (76, 1,754).
High-entropy prefixes sit at `32-63`, i.e. `32-63` reads more like a branching
intersection than a single special point.

**3.2 Empirical flow map — adjacent transitions.** Converting adjacent stage
rows into `state_t -> state_{t+1}` gives **9,806 observed adjacent transitions**
across **21 source states** and **17 destination states**, with the state coding
`band × boundary_front × chain_status`. The largest edges form a compact
downward band map (e.g. `16-31|near_exit_front|avoid -> 8-15|lower_edge_front|avoid`
at prob 0.974; `32-63|lower_edge_front|avoid_then_caught -> 16-31|near_exit_front|avoid`
at 0.760). Branching concentrates at a few `32-63` states; `4-7` is the main
capture-side receiving layer.

**3.3 Numeric trajectory anatomy — path shape instead of labels.** Reducing the
semantic labels and keeping the numeric path (`R_before`, `R_after`, `R_drop`,
`transition_k`, `exit_distance`, `remaining_K_before`) gives **2,750 trajectory
traces** from **12,556 numeric stage rows**. Terminal-aligned medians let one ask
where miss / control traces separate; a compact gradient signature shows miss
traces with a different terminal shape (median `exit_distance_slope = -0.800`,
`k_variation = 7.0`) from control/other traces (`0.100`, `5.0`). Here
`exit_distance` reads as a graded coordinate along the path rather than a front
label, and `32-63` looks less like a standalone object and more like a region
where the remaining-K trace is large enough for several nearby numeric shapes to
be visible.

**3.4 Paired numeric difference — local deformation of a shared road.**
Subtracting each matched control from its miss partner at terminal-aligned
indices gives **210 miss/control pairs** and **1,173 aligned pair-step rows**.
The differences collapse toward zero at the last indices (`-2, -1, 0` all median
0) while the visible separation sits at earlier steps (`-4`, `-3`). This reads as
a local deformation of a shared road rather than a separate route class.

**3.5 Alignment coordinate comparison — the view depends on the ruler.** Keeping
the same numeric rows but changing the alignment (terminal step, start step,
`exit_distance`, `R_before`) changes what is visible. Terminal alignment makes
the last steps collapse; start alignment asks where traces separate from the
entry side; `exit_distance` and `R_before` alignment turn trajectory-time into
coordinate slices (the largest single-slice difference, 28.00, appears under
`exit_distance` alignment at coordinate 0). The point is descriptive: the
apparent miss/control gap is partly a function of which coordinate is used as the
ruler.

---

## 4. Interpretation

Kept separate from the observations above, and deliberately limited.

- **Local event classification and chain status are different concepts.** One is
  a per-event label; the other is where that event sits within the max-depth
  avoidance run. They agree on many rows but come apart at `32-63`, so mixing
  them would misdescribe the split.
- **The controls read as position-displaced neighbours of the miss rows**, not a
  new shape family: same residue shapes, shifted in band position, landing in
  `drift` rather than `miss`.
- **The `32-63` split is best described as boundary-front plus chain status**,
  not as a different local label.
- **Across the atlas, `32-63` behaves like a branching intersection**, `4-7`
  like a capture-side sink, and the miss/control gap like a local deformation of
  a shared downward road. None of this is asserted beyond the audited rows.
- **The relevant object may be the geometry of leaving a dyadic band**, viewed
  through the boundary-aligned coordinate, rather than anything unique to
  `32-63`.

None of these interpretations asserts a mechanism, cause, generalization to all
integers, or any behaviour outside the audited rows.

---

## 5. Current safe summary

> We do not prove the Collatz conjecture; we construct a finite-sample
> coordinate atlas of observed accelerated trajectories.

日本語: コラッツ予想を証明しているのではなく、観測された加速軌道の有限サンプル座標アトラスを作っている。

The progression this note records is a change of *viewpoint* — from a
miss-vs-background classification to a finite trajectory atlas (routes, flow,
numeric paths, and coordinate slices) — not an increase in claim strength.

---

## 6. Limitations

- **Finite table only.** Every count, route, transition, and difference is a
  property of the specific CSV rows audited, not of the integers in general.
- **No proof.** Nothing here proves, or is evidence toward proving, any
  statement about Collatz trajectories beyond the observed rows.
- **No mechanism, no causality.** The audits describe co-occurrence and shape in
  a finite table; they do not explain why any row is a miss, a control, or a
  drift.
- **No global Collatz behavior.** No claim is made about all integers, all
  trajectories, unobserved bands, or asymptotic behaviour.
- **`control`, `miss`, `front`, `flow` are descriptive labels only.** They name
  rows, states, and views in this dataset. `control` is not an experimental
  control; `flow` is not a physical vector field; `front` is a boundary-aligned
  coordinate class.
- **Derived coordinates are not independent.** In particular
  `last_before_exit_distance = last_before_R − band_lower` is a display
  re-expression, not a new variable.
- **Labels come from joins.** Miss/control labels are attached at the trajectory
  level from the event-detail CSV, so route/flow/numeric tables indicate *which*
  routes carry those labels, not *why*.
- **This note is a derivative of `collatz-waiting-hall`, not a merge.** It does
  not modify the Waiting Hall chapter or the Paradoxical-Sequence chapter.

---

## 7. Files

### Reports (Markdown)

Part 2 core (controls / `32-63` split / boundary-front):

- `s_minus_m_control_exploration_report.md`
- `s_minus_m_depth2_chain_exploration_report.md`
- `paired_suffix_comparison_report.md`
- `boundary_transition_32_63_audit_report.md`
- `status_split_32_63_audit_report.md`
- `band_general_boundary_front_audit_report.md`

Atlas follow-ups:

- `trajectory_grammar_report.md`
- `empirical_flow_map_report.md`
- `numeric_trajectory_anatomy_report.md`
- `paired_numeric_difference_report.md`
- `alignment_coordinate_comparison_report.md`

### Supporting tables and figures

- control exploration: `miss_and_control_event_detail.csv`,
  `miss_vs_control_numeric_summary.csv`, `shape_position_cells.csv`,
  `s_minus_m_47_context_windows.csv`, `miss_and_control_context_windows.csv`,
  `s_minus_m_47_nearest_miss_by_shape.csv`,
  `miss_vs_control_exit_distance_transition_k.svg`,
  `miss_vs_control_R_before_after.svg`
- depth-controlled chain: `s_minus_m_47_chain_cards.md`,
  `s_minus_m_47_chain_cards.csv`,
  `control_miss_depth2_depth3_event_chain_detail.csv`,
  `depth_transition_table.csv`, `depth2_depth3_numeric_summary.csv`,
  `depth2_depth3_distributions.csv`, `s_minus_m_47_constant_coordinates.csv`,
  `s_minus_m_47_near_constant_coordinates.csv`,
  `s_minus_m_47_chain_pattern_counts.csv`
- paired suffix: `chain_stage_comparison_table.csv`,
  `stage_32_63_classification.csv`, `suffix_stage_class_summary.csv`,
  `per_control_paired_card_table.csv`, `per_control_paired_cards.md`,
  `control_clusters.csv`, `control_invariants_and_near_invariants.csv`,
  `miss_depth3_invariants_and_near_invariants.csv`
- `32-63` boundary transition: `boundary_transition_detail.csv`,
  `boundary_transition_frequency_table.csv`,
  `simple_boundary_front_selector_audit.csv`,
  `downstream_reconvergence_table.csv`,
  `boundary_transition_paired_examples.csv`
- band-general front: `band_stage_boundary_detail.csv`,
  `band_grouped_count_table.csv`, `band_front_distribution.csv`,
  `band_boundary_transition_frequencies.csv`,
  `band_compact_cross_band_table.csv`
- trajectory grammar: `trajectory_routes.csv`, `route_frequency_table.csv`,
  `miss_route_table.csv`, `control_route_table.csv`,
  `route_prefix_split_table.csv`, `route_suffix_convergence_table.csv`,
  `route_family_summary.csv`, `top_route_bar.png`,
  `miss_vs_control_route_bar.png`, `prefix_branching_entropy.png`,
  `suffix_convergence_entropy.png`, `route_tree_top_prefixes.png`
- empirical flow map: `transition_table.csv`, `branching_table.csv`,
  `convergence_table.csv`, `band_flow_summary.csv`,
  `miss_control_split_map.csv`, `transition_graph_top_edges.png`,
  `branching_entropy_by_state.png`, `band_to_band_flow_heatmap.png`
- numeric trajectory anatomy: `numeric_trajectory_table.csv`,
  `aligned_numeric_paths.csv`, `miss_control_numeric_path_summary.csv`,
  `route_difference_candidates.csv`, `numeric_path_cluster_table.csv`,
  `gradient_signature_table.csv`, `R_before_paths_overlay.png`,
  `R_drop_paths_overlay.png`, `k_paths_overlay.png`,
  `exit_distance_paths_overlay.png`, `miss_control_numeric_summary_heatmap.png`,
  `paired_route_difference_plot.png`
- paired numeric difference: `paired_numeric_differences.csv`,
  `paired_numeric_difference_summary.csv`, `local_jump_signature_table.csv`,
  `paired_R_before_difference.png`, `paired_R_drop_difference.png`,
  `paired_k_difference.png`, `paired_exit_distance_difference.png`,
  `paired_difference_heatmap.png`
- alignment coordinate comparison: `alignment_coordinate_signal_table.csv`,
  `terminal_alignment_difference_summary.csv`,
  `start_alignment_difference_summary.csv`,
  `exit_distance_alignment_difference_summary.csv`,
  `R_before_alignment_difference_summary.csv`,
  `paired_start_aligned_differences.csv`, `terminal_alignment_heatmap.png`,
  `start_alignment_heatmap.png`, `exit_distance_alignment_heatmap.png`,
  `R_before_alignment_heatmap.png`

---

*Finite-sample, observational, table-scoped. No proof, mechanism, cause,
counterexample, or global Collatz claim is made, and nothing is generalized to
all integers. This note is a derivative of `collatz-waiting-hall`; it is not the
same chapter and does not modify it.*
