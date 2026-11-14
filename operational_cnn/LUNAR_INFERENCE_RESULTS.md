# Lunar Terrain Operability Inference Results

## Run examined

This report describes the completed inference run:

```text
data/processed/terrain_operability_lunar_inference/
20261112T102554679130Z_3b8f93
```

Important files:

- `predictions.csv`: one row per lunar patch, with coordinates, physical summaries, class probabilities and crossing-axis predictions;
- `prediction_summary.csv`: class counts and fractions for each lunar region;
- `normalized_channel_summary.csv`: comparison of lunar channel values with the Earth training normalization;
- `provenance.json`: input hashes, configuration, completion status and claim boundary;
- `tensors/`: the five-channel physical tensors used for inference.

The run completed successfully with `status: complete`.

## What the inference means

The CNN was trained entirely on Earth terrain. The lunar terrain was divided into compatible, non-overlapping `960 m × 960 m` patches on a 30 m grid. Each patch therefore contains `32 × 32` cells and five channels:

1. patch-relative elevation;
2. slope;
3. 90 m roughness;
4. 330 m roughness;
5. Laplacian/terrain curvature.

The Earth training scaler was applied without being refitted on lunar data. The model then predicted:

- one of three macro-terrain classes: `operable`, `marginal` or `non_operable`;
- four undirected crossing axes: north–south, east–west, northwest–southeast and northeast–southwest.

These are Earth-trained predictions on unlabeled lunar terrain. They are not lunar accuracy measurements, certified rover-safety results or landing-site recommendations.

## Number of accepted lunar patches

Only complete windows were retained. Missing or incomplete terrain was excluded rather than treated as zero or suitable.

| Lunar region | Complete patches |
|---|---:|
| Leibnitz Beta Plateau | 225 |
| Malapert Massif | 400 |
| de Gerlache–Kocher Massif | 361 |
| Haworth | 841 |
| Faustini Rim A | 361 |
| de Gerlache Rim 2 | 361 |
| Connecting Ridge Extension | 361 |
| **Total** | **2,910** |

## Overall predictions

| Predicted class | Patches | Fraction |
|---|---:|---:|
| Operable | 1,022 | 35.1% |
| Marginal | 990 | 34.0% |
| Non-operable | 898 | 30.9% |

The model therefore divided the accepted lunar patches fairly evenly across the three generated classes.

## Predictions by lunar region

| Region | Operable | Marginal | Non-operable |
|---|---:|---:|---:|
| Haworth | **53.2%** | 31.2% | 15.7% |
| Faustini Rim A | **51.0%** | 30.2% | 18.8% |
| Leibnitz Beta Plateau | **40.9%** | 28.4% | 30.7% |
| de Gerlache Rim 2 | 30.5% | **44.0%** | 25.5% |
| Connecting Ridge Extension | 19.7% | **41.3%** | 39.1% |
| Malapert Massif | 15.8% | 22.5% | **61.8%** |
| de Gerlache–Kocher Massif | 15.2% | **43.5%** | 41.3% |

Under this model's terrain-only rule:

- Haworth and Faustini Rim A contain the largest fractions of terrain predicted `operable`;
- Malapert Massif contains the largest fraction predicted `non_operable`;
- de Gerlache–Kocher Massif and Connecting Ridge Extension contain large marginal or non-operable fractions.

This is not enough to call Haworth or Faustini the best landing or habitation site. The model does not consider illumination, temperature, communications, resources, landing hazards or other mission requirements.

## Agreement with physical terrain

The predicted classes follow a physically sensible progression:

| Predicted class | Median slope | Median 90th-percentile slope | Median relative relief |
|---|---:|---:|---:|
| Operable | 7.0° | 10.5° | 136 m |
| Marginal | 12.5° | 15.9° | 256 m |
| Non-operable | 19.3° | 21.8° | 401 m |

The broad relationship is:

```text
Flatter terrain and lower relief
                ↓
             Operable

Moderate slope and relief
                ↓
             Marginal

Steeper terrain and larger relief
                ↓
           Non-operable
```

This behavior is expected because the Earth development labels were generated from slope connectivity, and slope is one of the model inputs.

## Crossing-axis predictions

| Crossing axis | Fraction predicted positive |
|---|---:|
| North–south | 61.4% |
| East–west | 57.0% |
| Northwest–southeast | 47.3% |
| Northeast–southwest | 51.0% |

All 1,022 patches predicted `operable` were also predicted to support all four nominal crossing axes. All 898 patches predicted `non_operable` were predicted to support zero nominal crossing axes.

Marginal patches were more varied:

| Predicted nominal crossings | Fraction of marginal patches |
|---:|---:|
| 0 | 22.8% |
| 1 | 12.8% |
| 2 | 16.9% |
| 3 | 12.4% |
| 4 | 35.1% |

A patch can be classified `marginal` while having zero nominal crossings because the original Earth marginal label can be triggered by a crossing under the more permissive 20° scenario. The CNN's direction head predicts the nominal crossing targets.

The axes are undirected. For example, a positive north–south result does not distinguish north-to-south travel from south-to-north travel.

## Model probability

Median winning-class probabilities were:

| Predicted class | Median probability |
|---|---:|
| Operable | 90.8% |
| Marginal | 66.8% |
| Non-operable | 80.9% |

The model is least certain about marginal terrain, which is expected because it lies near the boundary between the two clearer classes.

Across all patches:

| Winning-class probability | Patches |
|---|---:|
| At most 50% | 34 |
| Above 50% through 70% | 989 |
| Above 70% through 90% | 1,187 |
| Above 90% | 700 |

There are 532 patches satisfying all three of these screening conditions:

```text
predicted operable
winning-class probability at least 90%
all four crossing axes predicted
```

These are suitable candidates for manual visual review. Model probability is not an operational rating or a calibrated probability of real rover safety.

## Example review candidate

The strongest predicted patch in this run is:

```text
Patch ID:              A3CLR22_2_Haworth:960:416:256
Region:                Haworth
Operable probability:  99.8%
Predicted crossings:   4 of 4
Median slope:          1.83°
90th-percentile slope: 4.15°
Relative relief:       23.0 m
Projected center X:    -44,760 m
Projected center Y:     92,460 m
```

The center coordinates are in the lunar south-polar projected coordinate system, not longitude and latitude.

This patch is a review candidate, not a validated destination.

## Earth-to-Moon distribution shift

The normalized-channel report shows that lunar slope and roughness are generally shifted above the Earth training means. Relative-elevation variation is also wider in some regions. Malapert Massif shows one of the strongest shifts.

Some lunar pixels therefore lie outside the model's most typical Earth training range. That does not automatically invalidate every prediction, but it means the CNN is performing cross-domain inference rather than ordinary in-distribution testing.

Review `normalized_channel_summary.csv` alongside predictions, especially where `fraction_abs_z_above_5` is elevated.

## Correct interpretation

The results support this statement:

> The Earth-trained CNN identifies lunar macro-terrain patches whose elevation, slope, roughness and curvature resemble the Earth patterns associated with the provisional generated operability classes.

They do not support these statements:

- the Moon predictions are 87.8% accurate;
- a predicted operable patch is safe for a rover;
- Haworth is the best landing site;
- a high model probability is a safety probability;
- the model accounts for all operational or human-habitability factors.

The 87.8% test accuracy belongs to the held-out Earth region, Death Valley. There are no lunar labels with which to calculate lunar accuracy.

## Recommended next step

Generate a map or visual gallery for every lunar region showing:

- the terrain raster;
- patch boundaries;
- predicted class colors;
- class probabilities;
- crossing-axis predictions;
- slope and relative-relief summaries;
- excluded incomplete areas.

Manual visual review should check whether predicted operable patches form coherent terrain zones and whether the model makes obvious mistakes around ridges, crater rims, steep barriers or data boundaries.
