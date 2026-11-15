# Terrain operability prototype

This package is separate from `terrain_similarity`. It builds provisional
directional route-connectivity labels, performs focused EDA and trains a small
multi-task CNN that imitates those generated labels.

The [terrain analysis notebook](notebooks/37_operational_terrain_eda.ipynb) explains the generated labels.
The [CNN experiment notebook](notebooks/38_operability_cnn_experiment.ipynb) trains and evaluates the model.

The current labels are scenario-based development evidence, not measured rover
safety. The model must not be used to claim lunar safety or habitability.

## Reproduce

Run from the repository root with a Python 3.12 environment:

```powershell
uv pip install --python .venv\Scripts\python.exe torch --index-url https://download.pytorch.org/whl/cpu
.venv\Scripts\python.exe -m unittest discover -s operational_cnn\tests -v
.venv\Scripts\python.exe -m operational_cnn.data.build_operability_eda --root .
.venv\Scripts\python.exe -m operational_cnn.review.build_review_gallery --root . --source-run <completed-eda-run>
.venv\Scripts\python.exe -m operational_cnn.training.train_operability --root .
```

The checked-in experiment configuration currently points at the first complete
EDA run. Every generated run records input hashes and finishes with complete or
failed provenance.
