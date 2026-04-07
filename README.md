# QDM Map Alignment

This repository contains a Python workflow for consistent alignment of repeated QDM measurements collected from the **same sample area** at different measurement steps.

In simple terms, the workflow uses the **LED / optical images** from two measurements to estimate how one image must be shifted, rotated, and slightly deformed to match the reference image. That transformation is then applied to the corresponding **QDM magnetic field map (`Bz`)**, so the maps can be compared in the same coordinate frame.

This is useful when you measure the same sample through a sequence of steps, for example during **AF demagnetisation**, and you want all QDM maps aligned to one reference step such as **NRM** or **AF0**.

## What this repository is for

Use this repository when you want to:
- align **one** QDM map to a reference map
- align a **series** of QDM maps from the same sample area to one common reference
- save the aligned field maps for later plotting, comparison, or interpretation

## Main files

### `alignment_functions.py`
This file contains the mathematical and image-processing functions used by the notebooks.

### `QDM_Alignment_Single.ipynb`
This notebook is for **single alignment**.

Use it when you want to align **one target map** to **one reference map**.

Typical example:
- reference = AF0 (NRM)
- target = one later step

### `QDM_Alignment_Batch.ipynb`
This notebook is for **batch alignment**.

Use it when you want to align **many maps** from the same sample area to **one reference map**.

Typical example:
- reference = AF0 (NRM)
- targets = all later AF steps from the same demagnetisation sequence

## Supported data formats

The workflow is designed around:
- `LED.jpg` for the optical image used for alignment
- `Bz` field files in one of these formats:
  - `.mat`
  - `.npy`
  - `.csv`

See [`docs/FORMATS.md`](docs/FORMATS.md) for details.

## Installation

See [`docs/INSTALLATION.md`](docs/INSTALLATION.md).

## How to use

See [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md).

## Warnings

See [`docs/WARNINGS_AND_LIMITATIONS.md`](docs/WARNINGS_AND_LIMITATIONS.md).

## Example data

`Testing_data/` is intended to contain a same-sample dataset, for example an AF demagnetisation sequence of ceramic samples.

You can cite the dataset as in [`docs/DATASET_AND_CITATION.md`](docs/DATASET_AND_CITATION.md).

