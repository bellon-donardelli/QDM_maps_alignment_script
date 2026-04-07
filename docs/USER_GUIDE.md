# User Guide

## What the workflow does

The workflow aligns repeated QDM measurements of the **same sample area**.

It does this in two steps:
1. it uses the LED / optical images to calculate how the target measurement should move to match the reference measurement
2. it applies that same transformation to the `Bz` field map

This gives you aligned magnetic maps that are easier to compare step by step.

---

## A. Single alignment

Use `QDM_Alignment_Single.ipynb` when you want to align **one target map** to **one reference map**.

### Typical use
- reference = `AF0` or `NRM`
- target = one later measurement step

### Before running
Make sure you have:
- `alignment_functions.py` in the repository root
- `QDM_Alignment_Single.ipynb` in the repository root
- a reference `LED.jpg`
- a target `LED.jpg`
- a target field file such as `Bz_uc0.mat`

### Basic workflow
1. Open `QDM_Alignment_Single.ipynb`
2. Edit the configuration cell
3. Set the reference LED path
4. Set the target LED path
5. Set the target field path
6. Choose the output directory
7. Run the notebook from top to bottom
8. Check the QC figures to make sure the alignment looks correct
9. Save or keep the aligned output file

### What the notebook should produce
Usually you will get:
- alignment QC figures for the LED images
- an aligned `Bz` file
- a QC figure for the aligned field map

---

## B. Batch alignment

Use `QDM_Alignment_Batch.ipynb` when you want to align **many maps** to the same reference.

### Typical use
You have a demagnetisation sequence where every folder is one measurement step from the same sample area.

Example idea:
- reference = `AF0`
- targets = `AF2_5`, `AF5`, `AF7_5`, `AF10`, and so on ...

### Expected folder idea
Each step folder should contain:
- `LED.jpg`
- one `Bz` file (`.mat`, `.npy`, or `.csv`)

### Basic workflow
1. Open `QDM_Alignment_Batch.ipynb`
2. Set the reference LED path
3. Set the parent batch directory
4. Check the output directory
5. Run the notebook from top to bottom
6. Review the QC output for each step
7. Check the summary table at the end

### What the batch notebook should produce
Usually you will get:
- one aligned field output per step
- QC plots for each aligned step
- a summary of alignment performance

---

## Important settings you may need to edit

### `MAT_KEY`
Use this if your `.mat` file stores the field under a name other than `Bz`.

### `SCALE`
Use this to convert units.

Example:
- `1e9` if your data is stored in Tesla and you want nT
- `1.0` if your data is already in the final units you want

### `FLIPUD`
Use this only if your QDM export convention requires vertical flipping.

### `VMIN` and `VMAX`
Use these to control color scaling in QC plots.

### `PIXEL_SIZE_UM`
Set this if you want the QC figure axes shown in micrometres instead of pixels.

---

## How to check whether the alignment worked

A good result usually shows:
- the sample outlines matching well in the LED overlay
- a smaller visual mismatch after alignment than before
- a reasonable affine transformation, not a clearly unrealistic one

If the result looks wrong:
- check that the reference and target images are from the same sample area
- check that the file paths are correct
- check that the correct `Bz` file was loaded
- try changing matching settings in the notebook
- inspect the LED images to see whether there are enough visible features
