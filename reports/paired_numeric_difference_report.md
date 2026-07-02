# Paired Numeric Difference Map

finite-sample observational note: this report looks only at observed suffix-matched miss/control numeric differences.

## What Changed

The previous view showed raw numeric paths. This view subtracts the matched control from the miss trajectory at each terminal-aligned reverse index, so the object is the local difference itself.

## Difference Summary

The map contains 210 miss/control pairs and 1,173 aligned pair-step rows. Positive values mean the miss trajectory is higher than its matched control at the same terminal-aligned index.

| reverse_step_index | pair_count | median_delta_R_before | median_delta_R_drop | median_delta_k | median_delta_exit_distance |
|---:|---:|---:|---:|---:|---:|
| -5 | 123 | -1.0 | -1.0 | -1.0 | -1.0 |
| -4 | 210 | 1.0 | 3.0 | 3.0 | 1.0 |
| -3 | 210 | 3.0 | 2.0 | 2.0 | 3.0 |
| -2 | 210 | 0.0 | 0.0 | 0.0 | 0.0 |
| -1 | 210 | 0.0 | 0.0 | 0.0 | 0.0 |
| 0 | 210 | 0.0 | 0.0 | 0.0 | 0.0 |

## Local Jump Candidates

The strongest local jumps are where the step-to-step movement difference is largest across the four numeric quantities.

| miss_trajectory | control_trajectory | max_jump_reverse_step_index | max_jump_score | d_R_before | d_R_drop | d_k | d_exit_distance |
|---|---|---:|---:|---:|---:|---:|---:|
| `Sample_D_random_550:555008` | `Sample_E_stratified_550:618657` | -2 | 32.0 | -7.0 | -9.0 | -9.0 | -7.0 |
| `Sample_C_higher_range_550:50027` | `Sample_C_higher_range_550:50331` | -2 | 30.0 | -8.0 | -7.0 | -7.0 | -8.0 |
| `Sample_E_stratified_550:464209` | `Sample_C_higher_range_550:50331` | -3 | 30.0 | -8.0 | -7.0 | -7.0 | -8.0 |
| `Sample_C_higher_range_550:50095` | `Sample_D_random_550:555169` | -3 | 30.0 | -7.0 | -8.0 | -8.0 | -7.0 |
| `Sample_D_random_550:353888` | `Sample_A_baseline:4551` | -1 | 28.0 | 8.0 | 6.0 | 6.0 | 8.0 |
| `Sample_E_stratified_550:830223` | `Sample_A_baseline:4551` | -2 | 28.0 | -7.0 | -7.0 | -7.0 | -7.0 |
| `Sample_E_stratified_550:573281` | `Sample_A_baseline:4551` | -1 | 28.0 | 8.0 | 6.0 | 6.0 | 8.0 |
| `Sample_E_stratified_550:490309` | `Sample_A_baseline:4551` | -1 | 28.0 | 8.0 | 6.0 | 6.0 | 8.0 |
| `Sample_E_stratified_550:854434` | `Sample_E_stratified_550:618657` | -3 | 26.0 | 5.0 | 8.0 | 8.0 | 5.0 |
| `Sample_A_baseline:4579` | `Sample_A_baseline:4551` | -3 | 24.0 | -6.0 | -6.0 | -6.0 | -6.0 |
| `Sample_D_random_550:588592` | `Sample_A_baseline:4551` | -3 | 24.0 | -6.0 | -6.0 | -6.0 | -6.0 |
| `Sample_E_stratified_550:61239` | `Sample_A_baseline:4551` | -3 | 24.0 | -6.0 | -6.0 | -6.0 | -6.0 |

## Reading

The difference view supports the small-but-local picture: many terminal positions collapse back toward zero, while the earlier aligned steps carry the visible miss/control separation. This is closer to a local deformation of a shared road than to a separate route class.

finite-sample observational note: these are difference maps for the available paired rows only, not a proof or mechanism.

## Output files

- `paired_numeric_differences.csv`
- `paired_numeric_difference_summary.csv`
- `local_jump_signature_table.csv`
- `paired_R_before_difference.png`
- `paired_R_drop_difference.png`
- `paired_k_difference.png`
- `paired_exit_distance_difference.png`
- `paired_difference_heatmap.png`