# QDM Map Alignment

This repository contains a Python workflow for consistent alignment of repeated QDM measurements collected from the **same sample area** at different measurement steps.

In simple terms, the workflow uses the **LED / optical images** from two measurements to estimate how one image must be shifted, rotated, and slightly deformed to match the reference image. That transformation is then applied to the corresponding **QDM magnetic field map (`Bz`)**, so the maps can be compared in the same coordinate frame.

This is useful when you measure the same sample through a sequence of steps, for example during **AF demagnetisation**, and you want all QDM maps aligned to one reference step such as **NRM** or **AF0**.

## What this repository is for

Use this repository when you want to:
- align **one** QDM map to a reference map
- align a **series** of QDM maps from the same sample area to one common reference
- save the aligned field maps for later plotting, comparison, or interpretation

## What you need to add before publishing or using the repo

This package was prepared **without** the source notebooks, the Python function file, or the data/output folders, because you said you will add them manually.

Add these files to the repository root:
- `alignment_functions.py`
- `QDM_Alignment_Single.ipynb`
- `QDM_Alignment_Batch.ipynb`

Add these folders if you want to include example data and example outputs:
- `Testing_data/`
- `aligned_output_single_alignment/`
- `aligned_output_batch_alignment/`

## Repository structure

After you add your own files, the repository should look like this:

```text
QDM_Map_Alignment/
├── README.md
├── requirements.txt
├── .gitignore
├── alignment_functions.py                # add manually
├── QDM_Alignment_Single.ipynb            # add manually
├── QDM_Alignment_Batch.ipynb             # add manually
├── Testing_data/                         # add manually if you want to publish example data
├── aligned_output_single_alignment/      # add manually if you want to publish example output
├── aligned_output_batch_alignment/       # add manually if you want to publish example output
└── docs/
    ├── INSTALLATION.md
    ├── USER_GUIDE.md
    ├── FORMATS.md
    ├── WARNINGS_AND_LIMITATIONS.md
    ├── DATASET_AND_CITATION.md
    └── PUBLISHING_CHECKLIST.md
```

## Main files

### `alignment_functions.py`
This file contains the mathematical and image-processing functions used by the notebooks.

Typical tasks handled there include:
- loading field data
- saving aligned field data
- estimating an affine transformation from LED images
- applying that affine transformation to the `Bz` map
- plotting quality-control figures

### `QDM_Alignment_Single.ipynb`
This notebook is for **single alignment**.

Use it when you want to align **one target map** to **one reference map**.

Typical example:
- reference = AF0 or NRM
- target = one later step

### `QDM_Alignment_Batch.ipynb`
This notebook is for **batch alignment**.

Use it when you want to align **many maps** from the same sample area to **one reference map**.

Typical example:
- reference = AF0 or NRM
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

If you publish the dataset in the repository, include the proper **Zenodo citation and DOI** in [`docs/DATASET_AND_CITATION.md`](docs/DATASET_AND_CITATION.md).

## Recommended citation

If you publish this repository, update the citation information with:
- authors
- year
- repository title
- version or release tag
- DOI, if you archive it on Zenodo
