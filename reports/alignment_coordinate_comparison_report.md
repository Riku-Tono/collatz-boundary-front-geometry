# Alignment Coordinate Comparison

finite-sample observational note: this report changes the alignment coordinate while keeping the same observed numeric rows.

## Motivation

The paired-difference audit showed that several variables collapse together under terminal suffix matching. This pass asks whether the view changes when the same data are aligned by start step, terminal step, exit_distance, or R_before.

## Coordinate Signal Table

| alignment | eligible_coordinate_count | best_coordinate | best_quantity | best_abs_difference |
|---|---:|---:|---|---:|
| reverse_step_index | 6 | -5 | R_before | 3.00 |
| start_step_index | 6 | 0 | R_drop | 4.00 |
| exit_distance | 3 | 0 | R_before | 28.00 |
| R_before | 6 | 9 | R_drop | 3.00 |

## Readout

Terminal alignment makes the last steps collapse, which is useful for seeing local deformation before convergence. Start alignment asks where the traces begin to separate from the entry side. Exit-distance and R_before alignment change the question from trajectory time to coordinate slices: what do miss/control rows look like at the same location in the local coordinate system?

## Top terminal coordinates

| alignment | coordinate | miss_count | control_count | other_count | miss_minus_control_R_before | miss_minus_other_R_before | miss_minus_control_R_drop | miss_minus_other_R_drop | miss_minus_control_transition_k | miss_minus_other_transition_k | miss_minus_control_exit_distance | miss_minus_other_exit_distance | score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| reverse_step_index | -5 | 29 | 16 | 194 | 3 | 3 | 2 | 2 | 2 | 2 | 3 | 3 | 3 |
| reverse_step_index | -4 | 111 | 47 | 1573 | 2 | 2 | 3 | 3 | 3 | 3 | 2 | 2 | 3 |
| reverse_step_index | -3 | 217 | 47 | 2140 | 3 | 3 | 1 | 1 | 1 | 1 | 3 | 3 | 3 |
| reverse_step_index | -1 | 228 | 47 | 2473 | 0 | 0 | -3 | -3 | -3 | -3 | 0 | 0 | 3 |
| reverse_step_index | -2 | 228 | 47 | 2406 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| reverse_step_index | 0 | 228 | 47 | 2475 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| reverse_step_index | -6 | 0 | 1 | 2 | NA | NA | NA | NA | NA | NA | NA | NA | NA |

## Top start coordinates

| alignment | coordinate | miss_count | control_count | other_count | miss_minus_control_R_before | miss_minus_other_R_before | miss_minus_control_R_drop | miss_minus_other_R_drop | miss_minus_control_transition_k | miss_minus_other_transition_k | miss_minus_control_exit_distance | miss_minus_other_exit_distance | score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| start_step_index | 0 | 228 | 47 | 2475 | 0 | 0 | 4 | 3 | 4 | 3 | 3 | 3 | 4 |
| start_step_index | 1 | 228 | 47 | 2473 | 0 | 0 | 1 | 1 | 1 | 1 | 2 | 2 | 2 |
| start_step_index | 2 | 228 | 47 | 2406 | -2 | -2 | -2 | -2 | -2 | -2 | -1 | -1 | 2 |
| start_step_index | 3 | 217 | 47 | 2140 | 0 | 0 | -1 | -1 | -1 | -1 | -1 | -1 | 1 |
| start_step_index | 4 | 111 | 47 | 1573 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| start_step_index | 5 | 29 | 16 | 194 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| start_step_index | 6 | 0 | 1 | 2 | NA | NA | NA | NA | NA | NA | NA | NA | NA |

## Top exit_distance coordinates

| alignment | coordinate | miss_count | control_count | other_count | miss_minus_control_R_before | miss_minus_other_R_before | miss_minus_control_R_drop | miss_minus_other_R_drop | miss_minus_control_transition_k | miss_minus_other_transition_k | score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| exit_distance | 0 | 366 | 148 | 5798 | -28 | -28 | 1 | 1 | 1 | 1 | 28 |
| exit_distance | 1 | 285 | 55 | 3345 | 0 | 0 | -3 | -1 | -3 | -1 | 3 |
| exit_distance | 2 | 123 | 49 | 1962 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| exit_distance | 3 | 155 | 0 | 46 | NA | 16 | NA | 0 | NA | 0 | NA |
| exit_distance | 4 | 75 | 0 | 18 | NA | 16 | NA | -2 | NA | -2 | NA |
| exit_distance | 5 | 21 | 0 | 33 | NA | 24 | NA | -3 | NA | -3 | NA |
| exit_distance | 6 | 7 | 0 | 15 | NA | 48 | NA | -1 | NA | -1 | NA |
| exit_distance | 7 | 5 | 0 | 32 | NA | 0 | NA | 0 | NA | 0 | NA |
| exit_distance | 8 | 4 | 0 | 4 | NA | 16 | NA | -2.5 | NA | -2.5 | NA |
| exit_distance | 9 | 0 | 0 | 7 | NA | NA | NA | NA | NA | NA | NA |
| exit_distance | 11 | 0 | 0 | 2 | NA | NA | NA | NA | NA | NA | NA |
| exit_distance | 13 | 0 | 0 | 1 | NA | NA | NA | NA | NA | NA | NA |

## Top R_before coordinates

| alignment | coordinate | miss_count | control_count | other_count | miss_minus_control_R_drop | miss_minus_other_R_drop | miss_minus_control_transition_k | miss_minus_other_transition_k | miss_minus_control_exit_distance | miss_minus_other_exit_distance | score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R_before | 9 | 206 | 47 | 2274 | -3 | -3 | -3 | -3 | 0 | 0 | 3 |
| R_before | 66 | 5 | 1 | 80 | -2 | -1 | -2 | -1 | 0 | 0 | 2 |
| R_before | 65 | 10 | 2 | 166 | 1 | 1 | 1 | 1 | 0 | 0 | 1 |
| R_before | 4 | 210 | 47 | 2324 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| R_before | 18 | 100 | 46 | 1638 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| R_before | 17 | 42 | 1 | 413 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| R_before | 33 | 25 | 1 | 430 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| R_before | 32 | 42 | 46 | 1660 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| R_before | 64 | 50 | 44 | 1343 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| R_before | 128 | 10 | 10 | 109 | 0 | -1 | 0 | -1 | 0 | 0 | 0 |
| R_before | 129 | 2 | 4 | 62 | 0 | -1 | 0 | -1 | 0 | 0 | 0 |
| R_before | 130 | 1 | 2 | 25 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

finite-sample observational note: these tables compare coordinate views only; they do not assert a mechanism.

## Output files

- `alignment_coordinate_signal_table.csv`
- `terminal_alignment_difference_summary.csv`
- `start_alignment_difference_summary.csv`
- `exit_distance_alignment_difference_summary.csv`
- `R_before_alignment_difference_summary.csv`
- `paired_start_aligned_differences.csv`
- `terminal_alignment_heatmap.png`
- `start_alignment_heatmap.png`
- `exit_distance_alignment_heatmap.png`
- `R_before_alignment_heatmap.png`