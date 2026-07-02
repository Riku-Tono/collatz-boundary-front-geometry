# Empirical Flow Map Report

finite-sample observational note: this report treats the rows as a finite empirical flow map on discrete states, not as a continuous physical vector field.

## 1. Motivation

The goal is to view the Collatz band material as movement across a finite state space. Instead of asking whether a single row is a miss or a control, the tables ask where a row sits, what state follows inside the same trajectory, and which states branch or receive flow in the observed sample.

## 2. State definition

The state used here is `band x boundary_front x chain_status`. In the source CSV this is implemented as `band`, `boundary_front_class`, and `stage_chain_status` from `band_stage_boundary_detail.csv`. The rendered label is `band|boundary_front|chain_status`.

## 3. Transition construction

Rows were sorted within `sample_id + trajectory_id` by `first_entry_index`, then adjacent rows were converted into `state_t -> state_t+1`. This produced 9,806 observed adjacent transitions across 21 source states and 17 destination states.

## 4. Main flow map

The largest edges are a compact downward band map. The most frequent transitions are:

| state | next_state | count | probability |
|---|---:|---:|---:|
| `16-31|near_exit_front|avoid` | `8-15|lower_edge_front|avoid` | 1,871 | 0.974 |
| `32-63|lower_edge_front|avoid_then_caught` | `16-31|near_exit_front|avoid` | 1,658 | 0.760 |
| `8-15|lower_edge_front|avoid` | `4-7|lower_edge_front|caught` | 1,536 | 0.608 |
| `64-127|lower_edge_front|avoid_then_caught` | `32-63|lower_edge_front|avoid_then_caught` | 1,492 | 0.963 |
| `8-15|lower_edge_front|avoid` | `4-7|lower_edge_front|avoid_then_caught` | 991 | 0.392 |
| `16-31|lower_edge_front|avoid` | `8-15|lower_edge_front|avoid` | 394 | 0.864 |
| `32-63|lower_edge_front|avoid_then_caught` | `16-31|lower_edge_front|avoid` | 314 | 0.144 |
| `16-31|lower_edge_front|avoid_then_caught` | `8-15|lower_edge_front|avoid` | 247 | 0.698 |
| `32-63|lower_edge_front|avoid_then_caught` | `16-31|lower_edge_front|avoid_then_caught` | 205 | 0.094 |
| `32-63|near_exit_front|avoid` | `16-31|near_exit_front|avoid` | 155 | 0.544 |
| `128-255|lower_edge_front|avoid_then_caught` | `64-127|lower_edge_front|avoid_then_caught` | 117 | 0.873 |
| `64-127|near_exit_front|avoid_then_caught` | `32-63|lower_edge_front|avoid_then_caught` | 90 | 0.882 |

The band summary keeps the same observation at a coarser scale:

| band | total_events | dominant_next_band | probability | mean_entropy_by_state |
|---|---:|---|---:|---:|
| 8-15 | 2,577 | 4-7 | 1.000 | 0.962 |
| 16-31 | 2,742 | 8-15 | 0.999 | 0.706 |
| 32-63 | 2,489 | 16-31 | 1.000 | 1.348 |
| 64-127 | 1,754 | 32-63 | 1.000 | 0.293 |
| 128-255 | 241 | 64-127 | 1.000 | 0.281 |
| 256-511 | 3 | 128-255 | 1.000 | 0.000 |

## 5. Branching and convergence

Branching is concentrated in a small number of observed states. Higher entropy means that the outgoing flow is less dominated by a single next state.

| state | total_outgoing | out_degree | entropy | top_next_state | top_next_probability |
|---|---:|---:|---:|---|---:|
| `32-63|lower_edge_front|caught` | 22 | 3 | 1.564 | `16-31|near_exit_front|avoid` | 0.409 |
| `32-63|near_exit_front|avoid` | 285 | 3 | 1.435 | `16-31|near_exit_front|avoid` | 0.544 |
| `16-31|lower_edge_front|avoid_then_caught` | 354 | 4 | 1.237 | `8-15|lower_edge_front|avoid` | 0.698 |
| `32-63|lower_edge_front|avoid_then_caught` | 2,182 | 4 | 1.044 | `16-31|near_exit_front|avoid` | 0.760 |
| `16-31|lower_edge_front|caught` | 2 | 2 | 1.000 | `8-15|lower_edge_front|avoid` | 0.500 |
| `8-15|lower_edge_front|avoid` | 2,527 | 2 | 0.966 | `4-7|lower_edge_front|caught` | 0.608 |
| `8-15|near_exit_front|avoid` | 50 | 2 | 0.958 | `4-7|lower_edge_front|avoid_then_caught` | 0.620 |
| `64-127|lower_edge_front|caught` | 66 | 2 | 0.716 | `32-63|lower_edge_front|avoid_then_caught` | 0.803 |
| `128-255|lower_edge_front|avoid_then_caught` | 134 | 3 | 0.673 | `64-127|lower_edge_front|avoid_then_caught` | 0.873 |
| `16-31|lower_edge_front|avoid` | 456 | 3 | 0.620 | `8-15|lower_edge_front|avoid` | 0.864 |

Convergence highlights states that receive the largest incoming flow:

| state | total_incoming | in_degree | top_prev_state | top_prev_probability |
|---|---:|---:|---|---:|
| `8-15|lower_edge_front|avoid` | 2,522 | 5 | `16-31|near_exit_front|avoid` | 0.742 |
| `16-31|near_exit_front|avoid` | 1,822 | 3 | `32-63|lower_edge_front|avoid_then_caught` | 0.910 |
| `32-63|lower_edge_front|avoid_then_caught` | 1,672 | 5 | `64-127|lower_edge_front|avoid_then_caught` | 0.892 |
| `4-7|lower_edge_front|caught` | 1,556 | 3 | `8-15|lower_edge_front|avoid` | 0.987 |
| `4-7|lower_edge_front|avoid_then_caught` | 1,025 | 3 | `8-15|lower_edge_front|avoid` | 0.967 |
| `16-31|lower_edge_front|avoid` | 371 | 3 | `32-63|lower_edge_front|avoid_then_caught` | 0.846 |
| `16-31|lower_edge_front|avoid_then_caught` | 291 | 3 | `32-63|lower_edge_front|avoid_then_caught` | 0.704 |
| `64-127|lower_edge_front|avoid_then_caught` | 220 | 4 | `128-255|lower_edge_front|avoid_then_caught` | 0.532 |
| `8-15|near_exit_front|avoid` | 160 | 5 | `16-31|lower_edge_front|avoid_then_caught` | 0.456 |
| `32-63|near_exit_front|avoid` | 82 | 3 | `64-127|lower_edge_front|avoid_then_caught` | 0.695 |

## 6. Miss/control split map

The split map uses event-level rows from `miss_and_control_event_detail.csv`, grouped by `band + boundary_front + residue_pair_mod32 + transition_k`. The event rows were joined back to the stage state by `sample_id + trajectory_id + band`, then assigned the dominant observed next state for that stage state.

| band | boundary_front | residue_pair_mod32 | transition_k | miss_count | control_count | dominant_miss_next_state | dominant_control_next_state |
|---|---|---|---:|---:|---:|---|---|
| 64-127 | near_exit_front | 4->31 | 5 | 11 | 1 | `32-63|lower_edge_front|avoid_then_caught` | `32-63|lower_edge_front|avoid_then_caught` |

## 7. Interpretation

The finite map is consistent with a layered grammar: `32-63` is visible as a branching layer rather than only as a special class; `64-127` contributes many mixed upstream entries; `16-31` and `8-15` mostly look like avoid-channel passage in this state coding; and `4-7` appears as the main capture-side receiving layer. The miss rows are better read here as trajectories passing through a particular flow grammar than as isolated labels.

## 8. Limits

The map depends on the source CSV definitions and on the finite sample represented there. The miss/control split table also uses a dominant-next-state join from stage states, so it should be read as a coarse comparison map rather than an event-level causal mechanism.

finite-sample observational note: the outputs are observation tables and figures for this dataset only; they do not assert proof, mechanism, generalization, counterexample, or any claim about the Collatz conjecture.

## Output files

- `transition_table.csv`
- `branching_table.csv`
- `convergence_table.csv`
- `band_flow_summary.csv`
- `miss_control_split_map.csv`
- `transition_graph_top_edges.png`
- `branching_entropy_by_state.png`
- `band_to_band_flow_heatmap.png`

## Source files

- `C:\Users\yauki\Documents\design\collatz\boundary-front geometry\boundary-front-geometry\csv\band_stage_boundary_detail.csv`
- `C:\Users\yauki\Documents\design\collatz\boundary-front geometry\boundary-front-geometry\csv\miss_and_control_event_detail.csv`