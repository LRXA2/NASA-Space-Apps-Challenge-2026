# Terrain operability prototype

This package is separate from `terrain_similarity`. It builds provisional
directional route-connectivity labels, performs focused EDA and trains a small
multi-task CNN that imitates those generated labels.

For the slow beginner walkthrough, start at
[`docs/00_START_HERE.md`](docs/00_START_HERE.md).

The current labels are scenario-based development evidence, not measured rover
safety. The model must not be used to claim lunar safety or habitability.

## Reproduce

From the D: project root with its Python 3.12 environment:

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
