# Warnings and Limitations

## 1. Same-sample requirement

This workflow is intended for repeated measurements of the **same sample area**.

Do not use it to align unrelated samples or different fields of view.

## 2. Alignment is driven by the LED image

The transformation is estimated from the **LED / optical image**, then applied to the `Bz` map.

If the LED image has poor contrast, blur, strong cropping differences, or too few visible features, the alignment may fail or be poor.

## 3. Check the result visually

Always inspect the figures.

Do not assume that a produced output is automatically correct just because the notebook finished running.

## 4. `.mat` compatibility

The loader is designed for standard MATLAB `.mat` files accessed through SciPy.

Some MATLAB v7.3 files may not load with `scipy.io.loadmat`.

If that happens, you may need to convert the file first or change the loading method in your own local code.

## 5. Unit conversion matters

If the scaling factor is wrong, your aligned output values will also be wrong.

Check whether your input field is stored in Tesla, nT, or another unit.

## 6. Vertical flip option

The `FLIPUD` option depends on the QDM export convention used for your data.

If the output looks vertically reversed, check this setting.

