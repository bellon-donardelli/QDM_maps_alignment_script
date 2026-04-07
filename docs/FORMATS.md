# File Formats

## Optical image input

The alignment workflow expects an optical or LED image, typically named:

```text
LED.jpg
```

This image is used to estimate the alignment transformation.

## Magnetic field input

The target magnetic field map can be provided as:
- `.mat`
- `.npy`
- `.csv`

## `.mat` files

The default variable name expected in a `.mat` file is usually:

```text
Bz
```

If your file uses another variable name, update the notebook setting:

```python
MAT_KEY = "your_variable_name"
```

## Saved output

The aligned field can be saved as:
- `.mat`
- `.npy`
- `.csv`

The exact format depends on the output path or notebook settings you use.

## Important naming notes

For batch processing, each step folder should normally include:
- `LED.jpg`
- one `Bz` file

A simple example is:

```text
Testing_data/
├── AF0/
│   ├── LED.jpg
│   └── Bz_uc0.mat
├── AF2_5/
│   ├── LED.jpg
│   └── Bz_uc0.mat
└── AF5/
    ├── LED.jpg
    └── Bz_uc0.mat
```

## Units

The code may apply a scaling factor during loading.

Common case:
- stored in Tesla
- multiplied by `1e9`
- displayed or saved in nT

If your data is already in the correct units, set the scale to `1.0`.
