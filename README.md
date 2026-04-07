# QDM Map Alignment

This repository contains a Python workflow for consistent alignment of repeated QDM measurements collected from the **same sample area** at different measurement steps.

In simple terms, the workflow uses the **LED / optical images** from two measurements to estimate how one image must be shifted, rotated, and slightly deformed to match the reference image. That transformation is then applied to the corresponding **QDM magnetic field map (`Bz`)**, so the maps can be compared in the same coordinate frame.

This is useful when you measure the same sample through a sequence of steps, for example during **AF demagnetisation**, and you want all QDM maps aligned to one reference step.

## Installation

See [`docs/INSTALLATION.md`](docs/INSTALLATION.md).

## How to use

See [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md).

## Warnings

See [`docs/WARNINGS_AND_LIMITATIONS.md`](docs/WARNINGS_AND_LIMITATIONS.md).

## Example data

`Testing_data/` is intended to contain a same-sample dataset, for example an AF demagnetisation sequence of ceramic samples.

You can cite the dataset as in [`docs/DATASET_AND_CITATION.md`](docs/DATASET_AND_CITATION.md).

