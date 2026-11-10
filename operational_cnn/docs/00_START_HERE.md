# Operational CNN — start here

This folder is the beginner-friendly walkthrough for the second CNN.

The tested implementation is now grouped with this walkthrough in the parent
[`operational_cnn`](../README.md) folder. The subfolders separate documentation,
configuration, data construction, labels, model code, training, review and tests.

## What this CNN is trying to answer

> Can a wheeled rover cross a 960 m terrain patch in a specified direction?

It does **not** currently answer whether a location is fully safe, habitable or
suitable for a lunar base.

## Learning order

| Step | Folder | Question |
| ---: | --- | --- |
| 1 | [`01_data`](01_data/README.md) | What exactly goes into the CNN? |
| 2 | [`02_labels`](02_labels/README.md) | How do we decide the expected answer? |
| 3 | [`03_model`](03_model/README.md) | What does the CNN do with the tensor? |
| 4 | [`04_training`](04_training/README.md) | How does it learn without data leakage? |
| 5 | [`05_evaluation`](05_evaluation/README.md) | How do we tell whether it works? |
| 6 | [`06_lunar_use`](06_lunar_use/README.md) | How can an Earth-trained model be used carefully on the Moon? |

## Current status

- Earth tensor and provisional-label pipeline: working.
- Five-region EDA run: complete.
- First prototype CNN: trained and geographically tested.
- Real rover-ground-truth labels: not yet available.
- Lunar inference: not started.

Start with Step 1 only. Do not worry about the CNN mathematics yet.

