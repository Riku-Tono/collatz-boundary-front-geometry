# Trajectory Grammar Report

finite-sample observational note: this report treats trajectory routes as a finite observational route dictionary over discrete states.

## 1. Motivation

The previous map counted local `state -> next_state` moves. This pass keeps each trajectory as an ordered route, so the main object is the state sequence itself: where a trajectory starts, which corridor it passes through, where it branches, and which suffixes recur.

## 2. Route construction

`band_stage_boundary_detail.csv` was sorted by `sample_id + trajectory_id + first_entry_index`. The state label is `band|boundary_front_class|stage_chain_status`. Consecutive repeated states were compressed, while the full uncompressed route was also retained. The resulting table contains 2,750 trajectories and 144 distinct compressed routes.

## 3. Most frequent routes

| compressed_route | count | probability | miss_count | control_count |
|---|---:|---:|---:|---:|
| `64-127|lower_edge_front|avoid_then_caught -> 32-63|lower_edge_front|avoid_then_caught -> 16-31|near_exit_front|avoid -> 8-15|lower_edge_front|avoid -> 4-7|lower_edge_front|caught` | 1,081 | 0.393 | 0 | 29 |
| `32-63|lower_edge_front|avoid_then_caught -> 16-31|near_exit_front|avoid -> 8-15|lower_edge_front|avoid -> 4-7|lower_edge_front|avoid_then_caught` | 146 | 0.053 | 0 | 0 |
| `64-127|lower_edge_front|avoid_then_caught -> 32-63|lower_edge_front|avoid_then_caught -> 16-31|lower_edge_front|avoid -> 8-15|lower_edge_front|avoid -> 4-7|lower_edge_front|avoid_then_caught` | 116 | 0.042 | 0 | 1 |
| `32-63|near_exit_front|avoid -> 16-31|near_exit_front|avoid -> 8-15|lower_edge_front|avoid -> 4-7|lower_edge_front|avoid_then_caught` | 105 | 0.038 | 62 | 0 |
| `32-63|lower_edge_front|avoid_then_caught -> 16-31|lower_edge_front|avoid -> 8-15|lower_edge_front|avoid -> 4-7|lower_edge_front|avoid_then_caught` | 95 | 0.035 | 0 | 0 |
| `128-255|lower_edge_front|avoid_then_caught -> 64-127|lower_edge_front|avoid_then_caught -> 32-63|lower_edge_front|avoid_then_caught -> 16-31|near_exit_front|avoid -> 8-15|lower_edge_front|avoid -> 4-7|lower_edge_front|caught` | 90 | 0.033 | 0 | 10 |
| `32-63|lower_edge_front|avoid_then_caught -> 16-31|near_exit_front|avoid -> 8-15|lower_edge_front|avoid -> 4-7|lower_edge_front|caught` | 82 | 0.030 | 0 | 0 |
| `32-63|lower_edge_front|avoid_then_caught -> 16-31|lower_edge_front|avoid_then_caught -> 8-15|lower_edge_front|avoid -> 4-7|lower_edge_front|avoid_then_caught` | 73 | 0.027 | 0 | 0 |
| `16-31|near_exit_front|avoid -> 8-15|lower_edge_front|avoid -> 4-7|lower_edge_front|avoid_then_caught` | 53 | 0.019 | 0 | 0 |
| `128-255|lower_edge_front|caught -> 64-127|lower_edge_front|avoid_then_caught -> 32-63|lower_edge_front|avoid_then_caught -> 16-31|near_exit_front|avoid -> 8-15|lower_edge_front|avoid -> 4-7|lower_edge_front|caught` | 49 | 0.018 | 0 | 3 |

## 4. Miss-bearing routes

| compressed_route | count | probability_within_miss_routes | miss_count | control_count |
|---|---:|---:|---:|---:|
| `32-63|near_exit_front|avoid -> 16-31|near_exit_front|avoid -> 8-15|lower_edge_front|avoid -> 4-7|lower_edge_front|avoid_then_caught` | 62 | 0.272 | 62 | 0 |
| `64-127|lower_edge_front|avoid_then_caught -> 32-63|near_exit_front|avoid -> 16-31|near_exit_front|avoid -> 8-15|lower_edge_front|avoid -> 4-7|lower_edge_front|avoid_then_caught` | 20 | 0.088 | 20 | 0 |
| `32-63|near_exit_front|avoid -> 16-31|lower_edge_front|avoid -> 8-15|lower_edge_front|avoid -> 4-7|lower_edge_front|avoid_then_caught` | 17 | 0.075 | 17 | 0 |
| `32-63|near_exit_front|avoid -> 16-31|lower_edge_front|avoid_then_caught -> 8-15|lower_edge_front|avoid -> 4-7|lower_edge_front|avoid_then_caught` | 13 | 0.057 | 13 | 0 |
| `128-255|near_exit_front|avoid_then_caught -> 64-127|lower_edge_front|avoid_then_caught -> 32-63|lower_edge_front|avoid_then_caught -> 16-31|near_exit_front|avoid -> 8-15|lower_edge_front|avoid -> 4-7|lower_edge_front|caught` | 11 | 0.048 | 11 | 1 |
| `64-127|near_exit_front|avoid -> 32-63|lower_edge_front|avoid_then_caught -> 16-31|near_exit_front|avoid -> 8-15|lower_edge_front|avoid -> 4-7|lower_edge_front|caught` | 11 | 0.048 | 11 | 0 |
| `64-127|near_exit_front|avoid_then_caught -> 32-63|lower_edge_front|avoid_then_caught -> 16-31|near_exit_front|avoid -> 8-15|lower_edge_front|avoid -> 4-7|lower_edge_front|caught` | 9 | 0.039 | 9 | 1 |
| `32-63|near_exit_front|avoid -> 16-31|lower_edge_front|avoid_then_caught -> 8-15|near_exit_front|avoid` | 8 | 0.035 | 8 | 0 |
| `128-255|lower_edge_front|avoid_then_caught -> 64-127|near_exit_front|avoid -> 32-63|lower_edge_front|avoid_then_caught -> 16-31|lower_edge_front|avoid_then_caught -> 8-15|lower_edge_front|avoid -> 4-7|lower_edge_front|avoid_then_caught` | 7 | 0.031 | 7 | 0 |
| `64-127|near_exit_front|avoid -> 32-63|lower_edge_front|avoid_then_caught -> 16-31|lower_edge_front|avoid -> 8-15|lower_edge_front|avoid -> 4-7|lower_edge_front|avoid_then_caught` | 6 | 0.026 | 6 | 0 |

## 5. Control-bearing routes

| compressed_route | count | probability_within_control_routes | miss_count | control_count |
|---|---:|---:|---:|---:|
| `64-127|lower_edge_front|avoid_then_caught -> 32-63|lower_edge_front|avoid_then_caught -> 16-31|near_exit_front|avoid -> 8-15|lower_edge_front|avoid -> 4-7|lower_edge_front|caught` | 29 | 0.617 | 0 | 29 |
| `128-255|lower_edge_front|avoid_then_caught -> 64-127|lower_edge_front|avoid_then_caught -> 32-63|lower_edge_front|avoid_then_caught -> 16-31|near_exit_front|avoid -> 8-15|lower_edge_front|avoid -> 4-7|lower_edge_front|caught` | 10 | 0.213 | 0 | 10 |
| `128-255|lower_edge_front|caught -> 64-127|lower_edge_front|avoid_then_caught -> 32-63|lower_edge_front|avoid_then_caught -> 16-31|near_exit_front|avoid -> 8-15|lower_edge_front|avoid -> 4-7|lower_edge_front|caught` | 3 | 0.064 | 0 | 3 |
| `128-255|near_exit_front|avoid_then_caught -> 64-127|lower_edge_front|avoid_then_caught -> 32-63|lower_edge_front|avoid_then_caught -> 16-31|near_exit_front|avoid -> 8-15|lower_edge_front|avoid -> 4-7|lower_edge_front|caught` | 1 | 0.021 | 11 | 1 |
| `64-127|near_exit_front|avoid_then_caught -> 32-63|lower_edge_front|avoid_then_caught -> 16-31|near_exit_front|avoid -> 8-15|lower_edge_front|avoid -> 4-7|lower_edge_front|caught` | 1 | 0.021 | 9 | 1 |
| `128-255|lower_edge_front|caught -> 64-127|lower_edge_front|avoid_then_caught -> 32-63|lower_edge_front|avoid_then_caught -> 16-31|near_exit_front|avoid -> 8-15|lower_edge_front|avoid -> 4-7|lower_edge_front|avoid_then_caught` | 1 | 0.021 | 0 | 1 |
| `256-511|lower_edge_front|caught -> 128-255|near_exit_front|avoid_then_caught -> 64-127|lower_edge_front|avoid_then_caught -> 32-63|lower_edge_front|avoid_then_caught -> 16-31|near_exit_front|avoid -> 8-15|lower_edge_front|avoid -> 4-7|lower_edge_front|caught` | 1 | 0.021 | 0 | 1 |
| `64-127|lower_edge_front|avoid_then_caught -> 32-63|lower_edge_front|avoid_then_caught -> 16-31|lower_edge_front|avoid -> 8-15|lower_edge_front|avoid -> 4-7|lower_edge_front|avoid_then_caught` | 1 | 0.021 | 0 | 1 |

## 6. Prefix branching

Prefixes show where the same initial route begins to split into different next states.

| prefix | total_count | out_degree | entropy | top_next_state | top_next_probability |
|---|---:|---:|---:|---|---:|
| `16-31|lower_edge_front|avoid_then_caught` | 63 | 4 | 1.627 | `8-15|lower_edge_front|avoid` | 0.508 |
| `32-63|lower_edge_front|avoid_then_caught` | 510 | 4 | 1.592 | `16-31|near_exit_front|avoid` | 0.465 |
| `32-63|lower_edge_front|caught` | 22 | 3 | 1.564 | `16-31|near_exit_front|avoid` | 0.409 |
| `64-127|lower_edge_front|caught -> 32-63|lower_edge_front|avoid_then_caught` | 53 | 3 | 1.529 | `16-31|near_exit_front|avoid` | 0.396 |
| `64-127|lower_edge_front|caught -> 32-63|near_exit_front|avoid` | 13 | 3 | 1.526 | `16-31|near_exit_front|avoid` | 0.462 |
| `64-127|lower_edge_front|avoid_then_caught -> 32-63|near_exit_front|avoid` | 56 | 3 | 1.511 | `16-31|near_exit_front|avoid` | 0.446 |
| `32-63|near_exit_front|avoid` | 203 | 3 | 1.399 | `16-31|near_exit_front|avoid` | 0.571 |
| `64-127|near_exit_front|avoid_then_caught -> 32-63|near_exit_front|avoid` | 10 | 3 | 1.371 | `16-31|near_exit_front|avoid` | 0.600 |
| `16-31|near_exit_front|avoid` | 98 | 5 | 1.311 | `8-15|lower_edge_front|avoid` | 0.704 |
| `32-63|near_exit_front|avoid -> 16-31|lower_edge_front|avoid_then_caught` | 53 | 4 | 1.238 | `8-15|lower_edge_front|avoid` | 0.623 |

## 7. Suffix convergence

Suffixes show where different earlier routes converge into the same ending grammar.

| suffix | total_count | in_degree | entropy | top_prev_state | top_prev_probability |
|---|---:|---:|---:|---|---:|
| `32-63|lower_edge_front|avoid_then_caught -> 16-31|lower_edge_front|avoid_then_caught -> 8-15|lower_edge_front|avoid -> 4-7|lower_edge_front|avoid_then_caught` | 62 | 4 | 1.659 | `64-127|lower_edge_front|avoid_then_caught` | 0.500 |
| `64-127|lower_edge_front|avoid_then_caught -> 32-63|lower_edge_front|avoid_then_caught -> 16-31|near_exit_front|avoid -> 8-15|lower_edge_front|avoid -> 4-7|lower_edge_front|caught` | 177 | 4 | 1.598 | `128-255|lower_edge_front|avoid_then_caught` | 0.514 |
| `8-15|lower_edge_front|avoid -> 4-7|lower_edge_front|avoid_then_caught` | 987 | 5 | 1.584 | `16-31|near_exit_front|avoid` | 0.442 |
| `64-127|lower_edge_front|avoid_then_caught -> 32-63|lower_edge_front|avoid_then_caught -> 16-31|lower_edge_front|avoid_then_caught -> 8-15|lower_edge_front|avoid -> 4-7|lower_edge_front|avoid_then_caught` | 10 | 3 | 1.571 | `128-255|lower_edge_front|avoid_then_caught` | 0.400 |
| `8-15|near_exit_front|avoid` | 111 | 5 | 1.524 | `16-31|lower_edge_front|avoid_then_caught` | 0.477 |
| `8-15|near_exit_front|avoid -> 4-7|lower_edge_front|avoid_then_caught` | 31 | 3 | 1.318 | `16-31|lower_edge_front|avoid_then_caught` | 0.613 |
| `8-15|lower_edge_front|avoid_then_caught` | 47 | 3 | 1.317 | `16-31|lower_edge_front|avoid_then_caught` | 0.532 |
| `32-63|near_exit_front|avoid -> 16-31|lower_edge_front|avoid -> 8-15|lower_edge_front|avoid -> 4-7|lower_edge_front|avoid_then_caught` | 16 | 3 | 1.299 | `64-127|lower_edge_front|avoid_then_caught` | 0.625 |
| `64-127|lower_edge_front|avoid_then_caught -> 32-63|lower_edge_front|avoid_then_caught -> 16-31|near_exit_front|avoid -> 8-15|lower_edge_front|avoid -> 4-7|lower_edge_front|avoid_then_caught` | 24 | 4 | 1.272 | `128-255|lower_edge_front|avoid_then_caught` | 0.667 |
| `32-63|lower_edge_front|avoid_then_caught -> 16-31|lower_edge_front|avoid -> 8-15|lower_edge_front|avoid -> 4-7|lower_edge_front|avoid_then_caught` | 170 | 5 | 1.271 | `64-127|lower_edge_front|avoid_then_caught` | 0.718 |

## 8. Route families

| route_family | route_count | trajectory_count | miss_count | control_count | miss_rate | notes |
|---|---:|---:|---:|---:|---:|---|
| capture_sink_4_7 | 105 | 2,581 | 210 | 47 | 0.817 | end_state contains 4-7 |
| branch_at_32_63 | 114 | 2,489 | 228 | 47 | 0.829 | 32-63 appears in a route with multiple observed next-state series |
| avoid_channel | 85 | 2,360 | 175 | 47 | 0.788 | 16-31 avoid followed by 8-15 avoid |
| near_front_avoid_route | 107 | 2,206 | 228 | 46 | 0.832 | route contains near_exit_front + avoid |
| upstream_mixed_64_127 | 76 | 1,754 | 118 | 47 | 0.715 | 64-127 appears upstream of multiple 32-63 states |
| short_lower_capture | 7 | 55 | 0 | 0 | 0.000 | short lower-edge route ending or passing through caught |

## 9. Interpretation

The route dictionary makes the band sequence more legible than isolated state counts. The common grammar runs downward through `32-63`, `16-31`, `8-15`, and into `4-7`, while several high-entropy prefixes show that `32-63` acts more like a branching intersection than a single special point. The `16-31 -> 8-15` avoid passage appears as a repeated channel, and many endings collect into a `4-7` capture-side suffix. Miss-bearing rows are therefore easier to read as traveling on a route grammar than as a single coordinate condition.

## 10. Limits

The route grammar is tied to the source CSV definitions and to the finite sample represented by those rows. The miss/control labels are attached at the trajectory level from `miss_and_control_event_detail.csv`, so they indicate which routes carry those observed event labels rather than explaining why they occur.

finite-sample observational note: these outputs are route dictionaries, split tables, and figures for this dataset only; they do not assert proof, mechanism, generalization, or any claim about the Collatz conjecture.

## Output files

- `trajectory_routes.csv`
- `route_frequency_table.csv`
- `miss_route_table.csv`
- `control_route_table.csv`
- `route_prefix_split_table.csv`
- `route_suffix_convergence_table.csv`
- `route_family_summary.csv`
- `top_route_bar.png`
- `miss_vs_control_route_bar.png`
- `prefix_branching_entropy.png`
- `suffix_convergence_entropy.png`
- `route_tree_top_prefixes.png`

## Source files

- `C:\Users\yauki\Documents\design\collatz\boundary-front geometry\boundary-front-geometry\csv\band_stage_boundary_detail.csv`
- `C:\Users\yauki\Documents\design\collatz\boundary-front geometry\boundary-front-geometry\csv\miss_and_control_event_detail.csv`