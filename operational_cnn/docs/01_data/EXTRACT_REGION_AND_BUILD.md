# Understanding `extract_region()` and `build()`

Source: [`build_operability_eda.py`](../../data/build_operability_eda.py)

These functions operate at different levels:

```text
build()
|-- extract_region(Atacama)
|-- extract_region(Death Valley)
|-- extract_region(Lanzarote)
|-- extract_region(Northern Arizona)
`-- extract_region(Wadi Rum)
```

- `extract_region()` creates tensors and labels for one Earth region.
- `build()` coordinates all five regions and saves the combined EDA results.

## 1. `extract_region()`

Simplified purpose:

> Load one region, find eligible patches, create five-channel tensors, generate provisional route labels, and save the tensors.

It receives:

```python
root      # project root
config    # experiment configuration
region    # for example, "death_valley"
run       # object that owns this output run
```

It returns:

```python
records      # information and labels for every eligible patch
origin_rows  # EDA results from shifting the patch grid
```

### Step 1: Load the region

```python
layers, (shape, transform, crs) = load_region(root, config, region)
```

`layers` contains aligned NumPy matrices:

```python
layers["elevation_m"]
layers["slope_deg"]
layers["roughness_90m"]
layers["local_elevation_std_m"]
layers["laplacian_per_m"]
layers["valid_input_mask"]
layers["natural_screen_mask"]
```

The remaining values mean:

- `shape`: number of rows and columns in the large raster;
- `transform`: converts pixel positions to map coordinates;
- `crs`: the region's coordinate reference system.

### Step 2: Check grid placement

```python
origin_rows = summarize_origin_counts(layers, region, config)
```

This checks whether slightly shifting the patch grid changes how many eligible
patches we obtain. It is an EDA check, not the final tensor extraction.

### Step 3: Prepare storage

```python
records = []
tensors_by_size = {600: [], 960: []}
```

`records` stores one dictionary per eligible patch.

The tensor lists are separate because their shapes differ:

```text
600 m tensor -> (5, 20, 20)
960 m tensor -> (5, 32, 32)
```

The first CNN uses the 960 m tensors.

### Step 4: Visit every candidate patch centre

```python
for size_m in config["patch_sizes_m"]:
    side = size_m // config["spacing_m"]

    for center_row, center_col in center_lattice(...):
```

For 960 m patches:

```python
side = 960 // 30
side = 32
```

The patch centre is converted into a top-left corner:

```python
row = center_row - side // 2
col = center_col - side // 2
```

The NumPy window becomes:

```python
window = np.s_[row:row + side, col:col + side]
```

### Step 5: Reject unusable patches

```python
ok, _, natural_fraction = eligibility(
    layers,
    window,
    config["minimum_natural_fraction"],
)

if not ok:
    continue
```

A patch is retained only when:

- every required terrain value is finite;
- every validity-mask pixel passes;
- at least 80% passes the Earth natural-terrain screen.

`continue` skips a rejected patch and moves to the next candidate centre.

### Step 6: Cut out five aligned matrices

```python
elevation = layers["elevation_m"][window]
slope = layers["slope_deg"][window]
rough90 = layers["roughness_90m"][window]
rough330 = layers["local_elevation_std_m"][window]
laplacian = layers["laplacian_per_m"][window]
```

The same window is used for every raster. Position `[10, 12]` in every matrix
therefore describes the same ground location.

### Step 7: Stack the matrices into a tensor

```python
tensor = np.stack((
    elevation - elevation.mean(),
    slope,
    rough90,
    rough330,
    laplacian,
)).astype(np.float32)
```

For a 960 m patch:

```text
Before: five separate (32, 32) matrices
After:  one (5, 32, 32) tensor
```

The elevation mean is removed so channel zero describes terrain shape relative
to the patch instead of absolute Earth elevation.

### Step 8: Store the tensor

```python
tensor_index = len(tensors_by_size[size_m])
tensors_by_size[size_m].append(tensor)
```

If the list already contains 100 tensors, the new tensor receives index 100.
The patch record stores this index so later code can retrieve the tensor.

### Step 9: Find the map coordinates

```python
x, y = transform * (center_col + 0.5, center_row + 0.5)
```

This converts pixel row/column coordinates into projected coordinates measured
in metres. The coordinates are also used to assign a 5 km spatial group.

### Step 10: Generate directional evidence

```python
scenario_results = {
    name: directional_connectivity(
        slope,
        values["hard_slope_deg"],
    )
    for name, values in config["scenarios"].items()
}
```

The slope patch is checked under three current scenarios:

| Scenario | Slope ceiling |
| --- | ---: |
| Conservative | 10 degrees |
| Nominal | 15 degrees |
| Permissive | 20 degrees |

Each scenario checks four crossings:

```text
north to south
east to west
northwest to southeast
northeast to southwest
```

These are generated development labels, not observed rover-safety truth.

### Step 11: Assign a display class

```python
label_class = operational_class(
    scenario_results["nominal"],
    scenario_results["permissive"],
    ...
)
```

The class is one of:

```text
operable
marginal
non_operable
```

The detailed directional results are retained; the class is only a simplified
summary.

### Step 12: Create the patch record

The record connects the tensor to its identity, location and label:

```python
record = {
    "patch_id": "death_valley:960:528:304",
    "region": "death_valley",
    "size_m": 960,
    "spatial_group": "death_valley:104:725",
    "natural_fraction": 0.91,
    "tensor_shard": "tensors/death_valley_960m.npz",
    "tensor_index": 100,
    "label_class": "marginal",
    "slope_p90_deg": 27.4,
}
```

The real record also stores terrain summaries and every scenario/direction
result, such as `nominal_north_south` and `permissive_crossing_count`.

### Step 13: Save the region tensors

After all patches are processed:

```python
values = np.stack(tensors)
```

For example:

```text
2,490 Northern Arizona patches
values.shape = (2490, 5, 32, 32)
```

They are saved in a compressed NumPy archive:

```python
np.savez_compressed(
    run.path("tensors/northern_arizona_960m.npz"),
    physical=values,
    channels=np.array(CHANNELS),
)
```

Finally:

```python
return records, origin_rows
```

## 2. `build()`

Simplified purpose:

> Run `extract_region()` for all five Earth regions, combine their records, create EDA summaries, and finalize provenance.

### Step 1: Read and validate configuration

```python
root = root.resolve()
config_path = config_path.resolve()
config = json.loads(config_path.read_text(encoding="utf-8"))
validate_config(config)
```

The JSON text becomes a Python dictionary. Validation happens before the large
terrain rasters are opened.

### Step 2: Start an isolated run

```python
with Run(root, "terrain_operability_eda", config, notebook) as run:
```

This creates a new directory under:

```text
data/processed/terrain_operability_eda/<new-run-id>/
```

`Run` records configuration, code hashes, inputs, outputs and whether execution
completed or failed.

### Step 3: Record important inputs

```python
run.input(config_path)
run.input(Path(__file__))
run.input(root / "operational_cnn/labels/route_labels.py")
```

These hashes identify the configuration, data builder and label code used.

### Step 4: Process all regions

```python
all_records = []
all_origins = []

for region in sorted(REGIONS):
    records, origins = extract_region(root, config, region, run)
    all_records.extend(records)
    all_origins.extend(origins)
```

`extract_region()` is called once per region. `extend()` combines the returned
lists into one flat collection.

### Step 5: Create the main patch table

```python
patches = pd.DataFrame(all_records)
```

Each patch dictionary becomes one row. Important columns include:

```text
patch_id
region
size_m
spatial_group
label_class
slope_p90_deg
nominal_north_south
```

The code rejects an empty table or duplicate patch IDs.

### Step 6: Save EDA tables

The function writes:

| File | Meaning |
| --- | --- |
| `patches.csv` | Every patch, label, location and tensor reference |
| `origin_sensitivity.csv` | Effect of shifting the patch grid |
| `label_summary.csv` | Counts and typical terrain by region/class |
| `class_balance.csv` | Fraction of each operational class |
| `feature_correlations.csv` | Relationships among terrain summaries |

### Step 7: Calculate class balance

The code counts the three classes separately for each patch size and calculates:

```python
class fraction = class count / all patches at that size
```

This tells us whether one class dominates the dataset.

### Step 8: Calculate feature correlations

For each region and size, the code compares:

- P90 slope;
- median 90 m roughness;
- median 330 m roughness;
- relative relief.

It uses Spearman correlation to ask whether two measurements generally increase
together. This is EDA, not proof that one feature is unnecessary.

### Step 9: Record limitations

The generated README and provenance explicitly state that:

- labels are generated from terrain rules;
- they do not certify rover safety;
- this stage did not train a CNN.

### Step 10: Finish the run

```python
return run.directory
```

When the `with Run(...)` block exits:

```text
Successful execution -> status: complete
Exception            -> status: failed
```

## Complete relationship

```text
build()
|
|-- Read and validate configuration
|-- Start a provenance-recorded run
|
|-- For each Earth region:
|   `-- extract_region()
|       |-- Load aligned rasters
|       |-- Check patch-grid origins
|       |-- Find eligible windows
|       |-- Stack five-channel tensors
|       |-- Generate provisional labels
|       |-- Create patch records
|       `-- Save tensor archives
|
|-- Combine all patch records
|-- Save CSV summaries
|-- Finalize provenance
`-- Return the completed run directory
```

## Key distinction

```text
extract_region() -> creates tensors and patch labels for one region

build()          -> coordinates all regions and creates the combined EDA run
```
