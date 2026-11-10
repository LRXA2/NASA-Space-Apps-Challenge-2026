# Step 1 — Understand the input data

This step answers one question:

> What does one example given to the operational CNN look like?

## 1. Start with a large Earth map

For each Earth region, we have large raster maps. A raster is a rectangular grid
of pixels, where every pixel stores a measurement about the same location.

The five current Earth regions are:

- Northern Arizona;
- Lanzarote;
- Atacama–San Pedro;
- Death Valley;
- Wadi Rum.

Every terrain pixel represents approximately `30 m × 30 m`.

## 2. Cut the map into patches

The first CNN experiment uses patches containing `32 × 32` pixels.

```text
32 pixels × 30 m = 960 m
```

Therefore, one patch represents approximately:

```text
960 m × 960 m of terrain
```

The EDA also checked 600 m patches, but the first CNN uses 960 m patches because
they fit the existing `32 × 32` CNN structure.

## 3. One location has five aligned maps

For every patch, we stack five terrain channels:

| Channel | Simple meaning |
| --- | --- |
| Relative elevation | Which parts are higher or lower than the patch average? |
| Slope | How steep is every pixel? |
| 90 m roughness | How much does elevation vary in a small neighbourhood? |
| 330 m roughness | How much does elevation vary across a broader neighbourhood? |
| Curvature | Where does the terrain bend into ridges or depressions? |

All five channels describe the same `32 × 32` locations.

The resulting tensor shape is:

```text
(5, 32, 32)
```

This means:

```text
5 terrain channels
32 rows
32 columns
```

When the CNN receives a batch, the shape becomes:

```text
(N, 5, 32, 32)
```

`N` is the number of patches in the batch.

## 4. Relative elevation is calculated per patch

The patch mean elevation is removed:

```text
relative elevation = elevation − patch mean elevation
```

Example:

```text
Original elevations:  [100, 110, 120]
Patch mean:            110
Relative elevations:  [-10, 0, 10]
```

This allows the model to compare terrain shape without treating an Earth site at
2,000 m above sea level as automatically different from lunar terrain because of
its absolute height datum.

## 5. Invalid data is not treated as safe

A patch is only admitted to the first training dataset when its required terrain
channels are complete. Missing terrain is not replaced with zero.

The Earth natural-terrain screen is used to select examples, but land-cover data
is not supplied to the CNN. That matters because lunar terrain has no Earth
WorldCover classes.

## 6. Nearby patches are grouped together

Every patch receives a 5 km spatial-group identifier.

```text
Nearby patches → same spatial group → same train/validation/test role
```

This prevents the CNN from training on one patch and being tested on an almost
identical neighbouring patch.

## 7. Current dataset size

At the primary 960 m scale, the current focused EDA produced:

| Region | Eligible patches |
| --- | ---: |
| Atacama–San Pedro | 4,948 |
| Death Valley | 1,592 |
| Lanzarote | 211 |
| Northern Arizona | 2,490 |
| Wadi Rum | 1,943 |
| **Total** | **11,184** |

These are many tensors, but they do not represent 11,184 fully independent
geographic sites. That is why spatial groups and whole-region testing remain
necessary.

## 8. Where the implementation lives

- Tensor/EDA builder: [`build_operability_eda.py`](../../data/build_operability_eda.py)
- Configuration: [`operability_config.json`](../../configs/operability_config.json)
- Complete EDA provenance: [`provenance.json`](../../../data/processed/terrain_operability_eda/20261110T130243908177Z_49a299/provenance.json)

You do not need to understand those files yet. For now, focus on the meaning of
the tensor.

## Check your understanding

Before Step 2, try answering:

1. Why does a `32 × 32` patch represent `960 m × 960 m`?
2. What does the `5` mean in `(5, 32, 32)`?
3. Why do we remove the patch’s mean elevation?
4. Why is WorldCover used for screening but not given to the CNN?
5. Why must nearby patches remain in the same dataset split?

