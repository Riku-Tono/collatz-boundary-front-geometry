# Numeric Trajectory Anatomy Report

finite-sample observational note: this report treats numeric traces as finite observed trajectories in the available CSV rows.

## 1. Motivation

The route grammar based on state labels was tidy, but it mostly showed the labels back to us. This pass reduces the role of semantic labels and asks what the numeric path itself looks like.

## 2. Why labels were reduced

The main path variables here are `R_before`, `R_after`, `R_drop`, `transition_k`, `exit_distance`, and `remaining_K_before`. The source columns are `last_before_R`, `last_after_R`, `boundary_k_num`, and `last_before_exit_distance` in `band_stage_boundary_detail.csv`; `remaining_K_before` is kept as the same local R coordinate for compatibility with the event tables. Band and miss/control are used only as auxiliary identifiers.

## 3. Numeric trajectory construction

The stage rows were ordered by `sample_id + trajectory_id + first_entry_index`. This produced 2,750 trajectory traces from 12,556 numeric stage rows. Each trajectory stores the full numeric sequences and compact summary features such as total drop, mean drop, max k, and exit-distance range.

## 4. Terminal-aligned paths

The terminal-aligned table sets the last observed stage to reverse index `0`, then indexes upstream stages as `-1`, `-2`, and so on. This makes capture-side convergence visible without using caught/avoid/front labels as the organizing axis.

## 5. Miss/control numeric comparison

Median summaries by reverse index show whether miss and control traces separate near the terminal side or earlier upstream. A compact view of the first aligned indices is:

| reverse_step_index | group | count | median_R_before | median_R_drop | median_k | median_exit_distance |
|---:|---|---:|---:|---:|---:|---:|
| -5 | control | 16 | 128.0 | 2.0 | 2.0 | 0.0 |
| -5 | miss | 29 | 131.0 | 4.0 | 4.0 | 3.0 |
| -5 | other | 194 | 128.0 | 2.0 | 2.0 | 0.0 |
| -4 | control | 47 | 64.0 | 1.0 | 1.0 | 0.0 |
| -4 | miss | 111 | 66.0 | 4.0 | 4.0 | 2.0 |
| -4 | other | 1573 | 64.0 | 1.0 | 1.0 | 0.0 |
| -3 | control | 47 | 32.0 | 3.0 | 3.0 | 0.0 |
| -3 | miss | 217 | 35.0 | 4.0 | 4.0 | 3.0 |
| -3 | other | 2140 | 32.0 | 3.0 | 3.0 | 0.0 |
| -2 | control | 47 | 18.0 | 4.0 | 4.0 | 2.0 |
| -2 | miss | 228 | 18.0 | 4.0 | 4.0 | 2.0 |
| -2 | other | 2406 | 18.0 | 4.0 | 4.0 | 2.0 |
| -1 | control | 47 | 9.0 | 5.0 | 5.0 | 1.0 |
| -1 | miss | 228 | 9.0 | 2.0 | 2.0 | 1.0 |
| -1 | other | 2473 | 9.0 | 5.0 | 5.0 | 1.0 |
| 0 | control | 47 | 4.0 | 4.0 | 4.0 | 0.0 |
| 0 | miss | 228 | 4.0 | 4.0 | 4.0 | 0.0 |
| 0 | other | 2475 | 4.0 | 4.0 | 4.0 | 0.0 |

## 6. Paired route differences

Miss trajectories were paired to control trajectories that shared a terminal band suffix of length 2-4, with transition-k suffix closeness used as a secondary preference. The table then records the first upstream index just outside the shared suffix window.

| shared_suffix_length | first_divergence_reverse_index | pair_count | median_delta_R_before | median_delta_R_drop | median_delta_k | median_delta_exit_distance |
|---:|---:|---:|---:|---:|---:|---:|
| 4 | -4 | 210 | 3.0 | 2.0 | 2.0 | 3.0 |

## 7. Numeric path clusters

A simple terminal-window clustering used the last six steps of `transition_k`, `R_drop`, and `exit_distance`, with missing upstream positions filled by column means after alignment. This is a shape grouping, not a semantic route family.

| cluster_id | trajectory_count | miss_count | control_count | miss_rate |
|---:|---:|---:|---:|---:|
| 2 | 1,425 | 15 | 38 | 0.283 |
| 1 | 584 | 3 | 2 | 0.600 |
| 8 | 174 | 46 | 0 | 1.000 |
| 4 | 138 | 4 | 0 | 1.000 |
| 3 | 136 | 54 | 1 | 0.982 |
| 5 | 123 | 90 | 0 | 1.000 |
| 7 | 113 | 15 | 0 | 1.000 |
| 6 | 57 | 1 | 6 | 0.143 |

## 8. Gradient signatures

The gradient signature table records simple shape features: R monotonicity, variation in drops, variation in k, exit-distance slope, total exit-distance change, local jumps, and a residence-like length counted from positive exit-distance stages.

| contains_miss | contains_control | count | median_exit_distance_slope | median_k_variation | median_total_variation_R_drop | median_residence_like_length |
|---|---|---:|---:|---:|---:|---:|
| False | False | 2475 | 0.100 | 5.0 | 5.0 | 2.0 |
| False | True | 47 | 0.100 | 5.0 | 5.0 | 2.0 |
| True | False | 228 | -0.800 | 7.0 | 7.0 | 3.0 |

## 9. Interpretation

The numeric view shifts attention from named route families to path shape. The terminal alignment makes it easy to ask whether miss/control share the same broad road and where their local numeric traces begin to separate. `exit_distance` can now be read as a graded coordinate along the path rather than as a front label, while `transition_k` appears as part of a short terminal shape instead of only as a family name. In this view, `32-63` is less a standalone object and more a region where the remaining-K trace is large enough for several nearby numeric shapes to be visible.

## 10. Limits

The broad trajectory table uses stage-level boundary rows, while miss/control labels come from the event-detail CSV. The pairing and clustering are intentionally simple first-pass devices for finding candidate numeric differences; they are not mechanisms.

finite-sample observational note: these outputs describe numeric path shapes in this dataset only; they do not assert proof, mechanism, generalization, counterexample, or any claim about the Collatz conjecture.

## Output files

- `numeric_trajectory_table.csv`
- `aligned_numeric_paths.csv`
- `miss_control_numeric_path_summary.csv`
- `route_difference_candidates.csv`
- `numeric_path_cluster_table.csv`
- `gradient_signature_table.csv`
- `R_before_paths_overlay.png`
- `R_drop_paths_overlay.png`
- `k_paths_overlay.png`
- `exit_distance_paths_overlay.png`
- `miss_control_numeric_summary_heatmap.png`
- `paired_route_difference_plot.png`

## Source files

- `C:\Users\yauki\Documents\design\collatz\boundary-front geometry\boundary-front-geometry\csv\band_stage_boundary_detail.csv`
- `C:\Users\yauki\Documents\design\collatz\boundary-front geometry\boundary-front-geometry\csv\miss_and_control_event_detail.csv`