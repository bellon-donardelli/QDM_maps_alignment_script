# Installation

## Recommended Python version

Use **Python 3.11, 3.12, or 3.13**.

A good simple choice is **Python 3.12** in a clean virtual environment.

## 1. Clone the repository

```bash
git clone <your-repository-url>
cd QDM_Map_Alignment
```

## 2. Create a virtual environment

### macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Windows
```bash
python -m venv .venv
.venv\Scripts\activate
```

## 3. Install the required packages

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## 4. Add your own source files

Copy these files into the repository root:
- `alignment_functions.py`
- `QDM_Alignment_Single.ipynb`
- `QDM_Alignment_Batch.ipynb`

## 5. Add your data folders if needed

If you want to ship example data and example outputs, add:
- `Testing_data/`
- `aligned_output_single_alignment/`
- `aligned_output_batch_alignment/`

## 6. Start Jupyter Notebook

```bash
python -m notebook
```

Then open:
- `QDM_Alignment_Single.ipynb` for one alignment
- `QDM_Alignment_Batch.ipynb` for multiple alignments

## 7. First thing to change in the notebooks

Replace any old hard-coded local paths with paths that match your own machine or repository layout.

For example, use paths like:

```python
REFERENCE_LED = "./Testing_data/AF0/LED.jpg"
TARGET_LED = "./Testing_data/AF2_5/LED.jpg"
TARGET_FIELD = "./Testing_data/AF2_5/Bz_uc0.mat"
```

## Notes

- `requirements.txt` is pinned to specific package versions so installation is more reproducible.
- If you already know your dataset only needs the notebooks, `notebook` and `ipykernel` are sufficient for the Jupyter side.
