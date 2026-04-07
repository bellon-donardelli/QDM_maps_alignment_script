"""
alignment_functions.py
──────────────────────
Utility functions for QDM map co-registration.

Workflow:
    1. label_edge_detection           – find label/colorbar boundaries (if needed)
    2. map_trimming                    – crop labels and colorbars (if needed)
    3. compute_affine_matrix           – ORB on raw LED images → affine matrix M
    4. compute_affine_matrix_enhanced  – ORB with filter cycling (Sobel/Laplacian/Unsharp/CLAHE)
    5. compute_affine_matrix_manual    – manual tie-point clicking (last resort)
    6. apply_affine                    – warp any 2-D array using a pre-computed M
    7. load_field_data                 – load Bz from .mat / .npy / .csv
    8. save_field_data                 – save aligned Bz to .mat / .npy / .csv

Authors: Bellon et al. 2026
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import matplotlib.gridspec as gridspec
from skimage import color, filters
import cv2
import scipy.io as sio
import os


# ──────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────

def _to_gray(img):
    """Convert any image (greyscale, RGB, RGBA) to float64 greyscale."""
    if img.ndim == 2:
        return img.astype(np.float64)
    if img.shape[2] == 4:
        return color.rgb2gray(img[:, :, :3])
    return color.rgb2gray(img)


def _to_u8(img):
    """Convert image to uint8, handling float and integer inputs."""
    if img.dtype in (np.float32, np.float64):
        return (np.clip(img, 0, 1) * 255).astype(np.uint8)
    return img.astype(np.uint8)


def _gray_u8(img):
    """Image → greyscale uint8."""
    u8 = _to_u8(img)
    if u8.ndim == 2:
        return u8
    return cv2.cvtColor(u8, cv2.COLOR_BGR2GRAY)


# ──────────────────────────────────────────────
# 1. Label / colorbar boundary detection
# ──────────────────────────────────────────────

def label_edge_detection(path, threshold_fraction=0.05, colorbar_fraction=0.90,
                         save_path=None, show=True):
    """
    Detect label and colorbar boundaries in an exported map image by
    profiling intensity gradients along the midlines.

    Parameters
    ----------
    path : str
        Path to the image file.
    threshold_fraction : float
        Fraction of max gradient used as detection threshold (default 0.05).
    colorbar_fraction : float
        Fraction of image width beyond which is assumed to be a colorbar
        (default 0.90).
    save_path : str or None
        If given, save the diagnostic plot to this path.
    show : bool
        Display the diagnostic plot inline.

    Returns
    -------
    left, right, top, bottom : int
        Pixel coordinates of the detected map boundaries.
    """
    img = mpimg.imread(path)
    gray = _to_gray(img)
    height, width = gray.shape

    # Mid-line intensity profiles
    h_profile = gray[height // 2, :]
    v_profile = gray[:, width // 2]

    # Absolute first derivatives
    dh = np.abs(np.diff(h_profile))
    dv = np.abs(np.diff(v_profile))

    thresh_h = np.max(dh) * threshold_fraction
    thresh_v = np.max(dv) * threshold_fraction

    # --- Horizontal: left boundary (first significant change L→R) ---
    h_idx_lr = np.where(dh > thresh_h)[0]
    left = int(h_idx_lr[0]) if len(h_idx_lr) > 0 else 0

    # --- Horizontal: right boundary (R→L, ignoring colorbar region) ---
    h_idx_rl = np.where(dh[::-1] > thresh_h)[0]
    valid_rl = [width - 1 - idx for idx in h_idx_rl]
    cb_limit = int(colorbar_fraction * width)
    valid_rl = [idx for idx in valid_rl if idx < cb_limit]

    # Find the plateau then take the third transition after it
    plateau_start = None
    for i in range(len(valid_rl) - 1):
        if abs(valid_rl[i] - valid_rl[i + 1]) > 10:
            plateau_start = valid_rl[i + 1]
            break

    if plateau_start is not None:
        after = [idx for idx in valid_rl if idx < plateau_start]
        right = int(after[2]) if len(after) >= 3 else int(after[-1]) if after else width - 1
    else:
        right = int(valid_rl[-1]) if valid_rl else width - 1

    # --- Vertical boundaries ---
    v_idx = np.where(dv > thresh_v)[0]
    top = int(v_idx[0]) if len(v_idx) > 0 else 0
    bottom = int(v_idx[-1]) if len(v_idx) > 0 else height - 1

    # --- Diagnostic plot ---
    fig, ax = plt.subplots(2, 1, figsize=(6, 10))

    ax[0].plot(h_profile, color="blue")
    ax[0].axvline(left, color='red', ls="--", label=f"Left = {left}")
    ax[0].axvline(right, color='green', ls="--", label=f"Right = {right}")
    ax[0].set_title("Horizontal mid-line intensity")
    ax[0].set_xlabel("Pixel"); ax[0].set_ylabel("Intensity")
    ax[0].legend(fontsize=7)

    ax[1].plot(v_profile, color="blue")
    ax[1].axvline(top, color='red', ls="--", label=f"Top = {top}")
    ax[1].axvline(bottom, color='green', ls="--", label=f"Bottom = {bottom}")
    ax[1].set_title("Vertical mid-line intensity")
    ax[1].set_xlabel("Pixel"); ax[1].set_ylabel("Intensity")
    ax[1].legend(fontsize=7)

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=300)
    if show:
        plt.show()
    else:
        plt.close(fig)

    return left, right, top, bottom


# ──────────────────────────────────────────────
# 2. Map trimming
# ──────────────────────────────────────────────

def map_trimming(image, left, right, top, bottom):
    """
    Crop an image array using the boundaries returned by label_edge_detection.

    Parameters
    ----------
    image : ndarray
        Input image (H, W) or (H, W, C).
    left, right, top, bottom : int
        Crop boundaries in pixels.

    Returns
    -------
    ndarray : cropped image.
    """
    if image.ndim == 3:
        return image[top:bottom, left:right, :]
    return image[top:bottom, left:right]


# ──────────────────────────────────────────────
# 3. Compute affine matrix — ORB on raw LEDs
# ──────────────────────────────────────────────

def compute_affine_matrix(reference_img, target_img, n_features=500,
                          n_matches=100, sample_name="alignment",
                          save_path=None, show=True):
    """
    ORB feature-match *target_img* to *reference_img* and return the
    2x3 affine transformation matrix that warps target -> reference.

    Parameters
    ----------
    reference_img, target_img : ndarray
        Images (uint8 or float 0-1, colour or greyscale).
    n_features : int
        Number of ORB features to detect (default 500).
    n_matches : int
        Max number of best matches used for estimateAffine2D (default 100).
    sample_name : str
        Label used in plot titles and saved filenames.
    save_path : str or None
        Directory to save the QC figure.  If None, not saved.
    show : bool
        Display the QC figure inline.

    Returns
    -------
    M : ndarray (2, 3) or None
        Affine matrix.  None if alignment failed.
    aligned_target : ndarray or None
        Target image warped onto the reference frame.
    n_inliers : int
        Number of RANSAC inliers (0 if alignment failed).
    """
    # Resize target to reference dimensions
    if reference_img.shape[:2] != target_img.shape[:2]:
        target_img = cv2.resize(target_img,
                                (reference_img.shape[1], reference_img.shape[0]),
                                interpolation=cv2.INTER_AREA)

    ref_u8 = _to_u8(reference_img)
    tgt_u8 = _to_u8(target_img)
    gray_ref = _gray_u8(reference_img)
    gray_tgt = _gray_u8(target_img)

    # ORB detect + match
    orb = cv2.ORB_create(nfeatures=n_features)
    kp1, des1 = orb.detectAndCompute(gray_ref, None)
    kp2, des2 = orb.detectAndCompute(gray_tgt, None)

    if des1 is None or des2 is None:
        print(f"[{sample_name}] ORB found no descriptors.")
        return None, None, 0

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = sorted(bf.match(des1, des2), key=lambda m: m.distance)

    n_use = min(n_matches, len(matches))
    if n_use < 3:
        print(f"[{sample_name}] Only {n_use} matches — need at least 3.")
        return None, None, 0

    src_pts = np.float32([kp1[m.queryIdx].pt for m in matches[:n_use]]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches[:n_use]]).reshape(-1, 1, 2)

    M, inliers = cv2.estimateAffine2D(dst_pts, src_pts)
    if M is None:
        print(f"[{sample_name}] estimateAffine2D failed.")
        return None, None, 0

    n_inliers = int(inliers.sum()) if inliers is not None else 0
    print(f"[{sample_name}] Affine matrix computed  —  {n_inliers}/{n_use} inliers")

    h, w = ref_u8.shape[:2]
    aligned_tgt = cv2.warpAffine(tgt_u8, M, (w, h))

    # --- QC figure ---
    diff_map = cv2.absdiff(ref_u8, aligned_tgt)
    overlay = cv2.addWeighted(ref_u8, 0.5, aligned_tgt, 0.7, 0)

    fig, axes = plt.subplots(2, 2, figsize=(12, 12))
    axes[0, 0].imshow(ref_u8, cmap="gray"); axes[0, 0].set_title("Reference")
    axes[0, 1].imshow(aligned_tgt, cmap="gray"); axes[0, 1].set_title("Aligned target")
    im = axes[1, 0].imshow(diff_map, cmap="hot"); axes[1, 0].set_title("Difference (pre -> post)")
    fig.colorbar(im, ax=axes[1, 0], shrink=0.5)
    axes[1, 1].imshow(overlay, cmap="gray"); axes[1, 1].set_title("Overlay")
    for ax in axes.ravel():
        ax.grid(True, alpha=0.3)
    plt.suptitle(f"LED alignment — {sample_name}", fontsize=10)
    plt.tight_layout()

    if save_path:
        fname = os.path.join(save_path, f"{sample_name}_LED_alignment.pdf")
        fig.savefig(fname, dpi=300, facecolor="w")
        print(f"  Saved: {fname}")
    if show:
        plt.show()
    else:
        plt.close(fig)

    return M, aligned_tgt, n_inliers


# ──────────────────────────────────────────────
# 4. Compute affine matrix — enhanced ORB with filter cycling (fallback)
# ──────────────────────────────────────────────

# --- Filter implementations ---

def _filter_sobel(gray, sigma=1.0):
    """Gaussian blur + Sobel gradient magnitude."""
    ksize = int(np.ceil(sigma * 6)) | 1
    blurred = cv2.GaussianBlur(gray, (ksize, ksize), sigma)
    gx = cv2.Sobel(blurred, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(blurred, cv2.CV_64F, 0, 1, ksize=3)
    mag = np.sqrt(gx**2 + gy**2)
    return (mag / mag.max() * 255).astype(np.uint8)


def _filter_laplacian(gray, sigma=1.0):
    """Gaussian blur + Laplacian (2nd derivative)."""
    ksize = int(np.ceil(sigma * 6)) | 1
    blurred = cv2.GaussianBlur(gray, (ksize, ksize), sigma)
    lap = cv2.Laplacian(blurred, cv2.CV_64F, ksize=3)
    lap = np.abs(lap)
    return (lap / lap.max() * 255).astype(np.uint8)


def _filter_unsharp(gray, sigma=1.0, strength=2.0):
    """Unsharp mask: original + strength * (original - blurred)."""
    ksize = int(np.ceil(sigma * 6)) | 1
    blurred = cv2.GaussianBlur(gray, (ksize, ksize), sigma)
    sharp = cv2.addWeighted(gray, 1.0 + strength, blurred, -strength, 0)
    return sharp


def _filter_clahe(gray, clip_limit=3.0, grid_size=8):
    """CLAHE — Contrast Limited Adaptive Histogram Equalisation."""
    clahe = cv2.createCLAHE(clipLimit=clip_limit,
                            tileGridSize=(grid_size, grid_size))
    return clahe.apply(gray)


# Filter registry: name -> (function, kwargs beyond gray and sigma)
_FILTER_REGISTRY = {
    "sobel":     (_filter_sobel, {}),
    "laplacian": (_filter_laplacian, {}),
    "unsharp":   (_filter_unsharp, {"strength": 2.0}),
    "clahe":     (_filter_clahe, {"clip_limit": 3.0, "grid_size": 8}),
}


def _try_orb_on_filtered(gray_ref, gray_tgt, filter_name, filter_func,
                          sigma, filter_kwargs, n_features, n_matches,
                          sample_name):
    """
    Apply a filter to both images, run ORB, return (M, n_inliers, enhanced_ref, enhanced_tgt)
    or (None, 0, ...) on failure.
    """
    # Apply filter
    if filter_name in ("clahe",):
        # CLAHE doesn't use sigma
        enh_ref = filter_func(gray_ref, **filter_kwargs)
        enh_tgt = filter_func(gray_tgt, **filter_kwargs)
    else:
        enh_ref = filter_func(gray_ref, sigma=sigma, **filter_kwargs)
        enh_tgt = filter_func(gray_tgt, sigma=sigma, **filter_kwargs)

    # ORB
    orb = cv2.ORB_create(nfeatures=n_features)
    kp1, des1 = orb.detectAndCompute(enh_ref, None)
    kp2, des2 = orb.detectAndCompute(enh_tgt, None)

    if des1 is None or des2 is None:
        return None, 0, enh_ref, enh_tgt

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = sorted(bf.match(des1, des2), key=lambda m: m.distance)

    n_use = min(n_matches, len(matches))
    if n_use < 3:
        return None, 0, enh_ref, enh_tgt

    src_pts = np.float32([kp1[m.queryIdx].pt for m in matches[:n_use]]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches[:n_use]]).reshape(-1, 1, 2)

    M, inliers = cv2.estimateAffine2D(dst_pts, src_pts)
    n_inliers = int(inliers.sum()) if (M is not None and inliers is not None) else 0

    return M, n_inliers, enh_ref, enh_tgt


def compute_affine_matrix_enhanced(reference_img, target_img, sigma=1.0,
                                   n_features=500, n_matches=100,
                                   min_inliers=10,
                                   filters=None,
                                   sample_name="alignment",
                                   save_path=None, show=True):
    """
    Fallback alignment that cycles through image enhancement filters
    until one produces enough inliers.

    Filters tried in order (unless overridden):
        1. Sobel gradient magnitude
        2. Laplacian (2nd derivative)
        3. Unsharp mask
        4. CLAHE (adaptive histogram equalisation)

    Parameters
    ----------
    reference_img, target_img : ndarray
        Images (uint8 or float 0-1, colour or greyscale).
    sigma : float
        Gaussian blur sigma used by Sobel, Laplacian, and Unsharp filters
        (default 1.0).
    n_features : int
        Number of ORB features to detect (default 500).
    n_matches : int
        Max number of best matches used for estimateAffine2D (default 100).
    min_inliers : int
        Minimum inliers to accept a result before trying the next filter
        (default 10).
    filters : list of str or None
        Which filters to try, in order. Choose from:
        "sobel", "laplacian", "unsharp", "clahe".
        If None, tries all four in the order above.
    sample_name : str
        Label used in plot titles and saved filenames.
    save_path : str or None
        Directory to save the QC figure.  If None, not saved.
    show : bool
        Display the QC figure inline.

    Returns
    -------
    M : ndarray (2, 3) or None
        Affine matrix.  None if all filters failed.
    aligned_target : ndarray or None
        Target image warped onto the reference frame (original image).
    n_inliers : int
        Number of RANSAC inliers (0 if all failed).
    """
    if filters is None:
        filters = ["sobel", "laplacian", "unsharp", "clahe"]

    # Resize target to reference dimensions
    if reference_img.shape[:2] != target_img.shape[:2]:
        target_img = cv2.resize(target_img,
                                (reference_img.shape[1], reference_img.shape[0]),
                                interpolation=cv2.INTER_AREA)

    ref_u8 = _to_u8(reference_img)
    tgt_u8 = _to_u8(target_img)
    gray_ref = _gray_u8(reference_img)
    gray_tgt = _gray_u8(target_img)

    best_M = None
    best_inliers = 0
    best_filter = None
    best_enh_ref = None
    best_enh_tgt = None

    for fname in filters:
        if fname not in _FILTER_REGISTRY:
            print(f"[{sample_name}] Unknown filter '{fname}' — skipped.")
            continue

        func, kwargs = _FILTER_REGISTRY[fname]

        M, n_inl, enh_ref, enh_tgt = _try_orb_on_filtered(
            gray_ref, gray_tgt, fname, func,
            sigma, kwargs, n_features, n_matches, sample_name
        )

        status = f"{n_inl} inliers" if M is not None else "failed"
        print(f"  [{sample_name}] filter={fname:<12s}  {status}")

        # Keep the best result seen so far
        if n_inl > best_inliers:
            best_M = M
            best_inliers = n_inl
            best_filter = fname
            best_enh_ref = enh_ref
            best_enh_tgt = enh_tgt

        # Stop early if we have enough
        if best_inliers >= min_inliers:
            break

    if best_M is None:
        print(f"[{sample_name}] All filters failed.")
        return None, None, 0

    print(f"[{sample_name}] Best filter: {best_filter}  ({best_inliers} inliers)")

    # Warp the ORIGINAL target
    h, w = ref_u8.shape[:2]
    aligned_tgt = cv2.warpAffine(tgt_u8, best_M, (w, h))

    # --- QC figure ---
    diff_map = cv2.absdiff(ref_u8, aligned_tgt)
    overlay = cv2.addWeighted(ref_u8, 0.5, aligned_tgt, 0.7, 0)

    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    axes[0, 0].imshow(best_enh_ref, cmap="gray")
    axes[0, 0].set_title(f"Reference — {best_filter}")
    axes[0, 1].imshow(best_enh_tgt, cmap="gray")
    axes[0, 1].set_title(f"Target — {best_filter}")
    axes[0, 2].imshow(aligned_tgt, cmap="gray")
    axes[0, 2].set_title("Aligned target (original)")
    im = axes[1, 0].imshow(diff_map, cmap="hot")
    axes[1, 0].set_title("Difference")
    fig.colorbar(im, ax=axes[1, 0], shrink=0.5)
    axes[1, 1].imshow(overlay, cmap="gray")
    axes[1, 1].set_title("Overlay")
    axes[1, 2].imshow(ref_u8, cmap="gray")
    axes[1, 2].set_title("Reference (original)")
    for ax in axes.ravel():
        ax.grid(True, alpha=0.3)
    plt.suptitle(f"Enhanced alignment — {sample_name}  (best: {best_filter})", fontsize=10)
    plt.tight_layout()

    if save_path:
        fname_out = os.path.join(save_path,
                                 f"{sample_name}_LED_{best_filter}_alignment.pdf")
        fig.savefig(fname_out, dpi=300, facecolor="w")
        print(f"  Saved: {fname_out}")
    if show:
        plt.show()
    else:
        plt.close(fig)

    return best_M, aligned_tgt, best_inliers

# ──────────────────────────────────────────────
# 5. Manual tie-point alignment (last resort)
# ──────────────────────────────────────────────

def compute_affine_matrix_manual(reference_img, target_img, n_points=6,
                                 sample_name="manual",
                                 save_path=None, show=True):
    """
    Manual alignment by clicking corresponding tie-points on a side-by-side view.

    Both images are shown simultaneously. For each point pair you:
      1. Click on the reference (left panel)
      2. Click on the target (right panel)
    Points are numbered and colour-coded so you can track them.
    After all pairs are picked, you can accept or redo.

    Pick more points than the minimum (3) so that RANSAC can reject
    any misclicked pairs.  Default is 6.

    IMPORTANT: Requires an interactive matplotlib backend.
    Run this in your notebook BEFORE calling this function:
        %matplotlib tk
    (or %matplotlib qt)
    You can switch back afterwards with:
        %matplotlib inline

    Parameters
    ----------
    reference_img, target_img : ndarray
        Images (uint8 or float 0-1, colour or greyscale).
    n_points : int
        Number of tie-point pairs to pick (default 6, minimum 3).
    sample_name : str
        Label used in plot titles and saved filenames.
    save_path : str or None
        Directory to save the QC figure.
    show : bool
        Display the QC figure inline.

    Returns
    -------
    M : ndarray (2, 3) or None
        Affine matrix.  None if not enough points or user cancelled.
    aligned_target : ndarray or None
        Target image warped onto the reference frame.
    n_points_used : int
        Number of point pairs actually used.
    """
    if n_points < 3:
        print("Need at least 3 point pairs. Setting n_points = 3.")
        n_points = 3

    # Resize target to reference dimensions
    if reference_img.shape[:2] != target_img.shape[:2]:
        target_img = cv2.resize(target_img,
                                (reference_img.shape[1], reference_img.shape[0]),
                                interpolation=cv2.INTER_AREA)

    ref_u8 = _to_u8(reference_img)
    tgt_u8 = _to_u8(target_img)

    # Colours for point labels
    colors = plt.cm.tab10(np.linspace(0, 1, max(n_points, 10)))

    accepted = False
    ref_pts = []
    tgt_pts = []

    while not accepted:
        ref_pts = []
        tgt_pts = []

        fig, (ax_ref, ax_tgt) = plt.subplots(1, 2, figsize=(18, 8))
        ax_ref.imshow(ref_u8, cmap="gray")
        ax_ref.set_title("REFERENCE  —  click here first for each pair", fontsize=11)
        ax_ref.grid(True, alpha=0.3)

        ax_tgt.imshow(tgt_u8, cmap="gray")
        ax_tgt.set_title("TARGET  —  then click corresponding point here", fontsize=11)
        ax_tgt.grid(True, alpha=0.3)

        fig.suptitle(f"Pick {n_points} point pairs: click LEFT then RIGHT, alternating.\n"
                     f"(right-click or middle-click to undo last point, Enter to finish early)",
                     fontsize=10)
        plt.tight_layout()

        print(f"\n{'='*60}")
        print(f"  Pick {n_points} tie-point pairs on the side-by-side view.")
        print(f"  For each pair: click REFERENCE (left) then TARGET (right).")
        print(f"  Press Enter to finish early if you have >= 3 pairs.")
        print(f"{'='*60}\n")

        # Collect 2*n_points clicks (alternating ref, tgt)
        all_clicks = plt.ginput(2 * n_points, timeout=0)
        plt.close(fig)

        if len(all_clicks) < 6:  # need at least 3 pairs = 6 clicks
            print(f"Only {len(all_clicks)} clicks — need at least 6 (3 pairs).")
            return None, None, 0

        # Separate into ref and tgt based on x-coordinate
        # Left panel = reference, right panel = target
        # The figure has two axes; we need to figure out which axis each click was on.
        # With ginput on the figure, x coords in the left panel are in ref pixel space,
        # and right panel coords are offset. Instead, let's use the simpler approach:
        # odd clicks (0, 2, 4...) = reference, even clicks (1, 3, 5...) = target

        for i in range(0, len(all_clicks) - 1, 2):
            ref_pts.append(all_clicks[i])
            tgt_pts.append(all_clicks[i + 1])

        n_pairs = len(ref_pts)
        if n_pairs < 3:
            print(f"Only {n_pairs} complete pairs — need at least 3.")
            return None, None, 0

        # Show summary with points plotted
        fig2, (ax_r, ax_t) = plt.subplots(1, 2, figsize=(18, 8))
        ax_r.imshow(ref_u8, cmap="gray")
        ax_r.set_title("Reference — your picks")
        ax_r.grid(True, alpha=0.3)

        ax_t.imshow(tgt_u8, cmap="gray")
        ax_t.set_title("Target — your picks")
        ax_t.grid(True, alpha=0.3)

        print(f"\n  {n_pairs} point pairs collected:")
        for i, (rp, tp) in enumerate(zip(ref_pts, tgt_pts)):
            c = colors[i % len(colors)]
            ax_r.plot(rp[0], rp[1], '+', color=c, markersize=14, markeredgewidth=2)
            ax_r.annotate(str(i+1), (rp[0]+5, rp[1]-5), color=c,
                         fontsize=11, fontweight='bold')
            ax_t.plot(tp[0], tp[1], '+', color=c, markersize=14, markeredgewidth=2)
            ax_t.annotate(str(i+1), (tp[0]+5, tp[1]-5), color=c,
                         fontsize=11, fontweight='bold')
            print(f"    {i+1}. ref=({rp[0]:.1f}, {rp[1]:.1f})  ->  tgt=({tp[0]:.1f}, {tp[1]:.1f})")

        fig2.suptitle(f"Review your {n_pairs} point pairs — close this window to continue",
                      fontsize=11)
        plt.tight_layout()
        plt.show(block=True)

        # Ask user to accept or redo
        response = input("\n  Accept these points? (y = accept / n = redo / q = cancel): ").strip().lower()
        if response == 'q':
            print("  Cancelled.")
            return None, None, 0
        elif response == 'y' or response == 'yes':
            accepted = True
        else:
            print("  Redoing point picking...\n")

    n_used = len(ref_pts)

    # --- Compute affine matrix ---
    # ginput returns figure coordinates; for the side-by-side layout,
    # left panel clicks are in data coords of ax_ref, right panel in ax_tgt.
    # With plt.ginput on the figure level, we need to handle this carefully.
    # The ref clicks should already be in ref image pixel coords,
    # and tgt clicks in tgt image pixel coords since both axes show
    # their respective images at [0, w] x [0, h].

    src = np.float32(ref_pts).reshape(-1, 1, 2)
    dst = np.float32(tgt_pts).reshape(-1, 1, 2)

    M, inliers = cv2.estimateAffine2D(dst, src)
    if M is None:
        print("  estimateAffine2D failed on manual points.")
        return None, None, 0

    n_inliers = int(inliers.sum()) if inliers is not None else 0
    print(f"\n  Affine matrix computed — {n_inliers}/{n_used} inliers (RANSAC)")

    if inliers is not None:
        outliers = [i for i, v in enumerate(inliers.ravel()) if v == 0]
        if outliers:
            print(f"  Points rejected by RANSAC: {[i+1 for i in outliers]}")

    # Warp target
    h, w = ref_u8.shape[:2]
    aligned_tgt = cv2.warpAffine(tgt_u8, M, (w, h))

    # --- QC figure ---
    diff_map = cv2.absdiff(ref_u8, aligned_tgt)
    overlay = cv2.addWeighted(ref_u8, 0.5, aligned_tgt, 0.7, 0)

    fig, axes = plt.subplots(2, 3, figsize=(16, 10))

    axes[0, 0].imshow(ref_u8, cmap="gray")
    for i, pt in enumerate(ref_pts):
        c = colors[i % len(colors)]
        marker = '+' if (inliers is not None and inliers.ravel()[i]) else 'x'
        axes[0, 0].plot(pt[0], pt[1], marker, color=c, markersize=12, markeredgewidth=2)
        axes[0, 0].annotate(str(i+1), (pt[0]+5, pt[1]-5), color=c, fontsize=9)
    axes[0, 0].set_title("Reference + tie-points (x = rejected)")

    axes[0, 1].imshow(tgt_u8, cmap="gray")
    for i, pt in enumerate(tgt_pts):
        c = colors[i % len(colors)]
        marker = '+' if (inliers is not None and inliers.ravel()[i]) else 'x'
        axes[0, 1].plot(pt[0], pt[1], marker, color=c, markersize=12, markeredgewidth=2)
        axes[0, 1].annotate(str(i+1), (pt[0]+5, pt[1]-5), color=c, fontsize=9)
    axes[0, 1].set_title("Target + tie-points (x = rejected)")

    axes[0, 2].imshow(aligned_tgt, cmap="gray")
    axes[0, 2].set_title("Aligned target")

    im = axes[1, 0].imshow(diff_map, cmap="hot")
    axes[1, 0].set_title("Difference")
    fig.colorbar(im, ax=axes[1, 0], shrink=0.5)

    axes[1, 1].imshow(overlay, cmap="gray")
    axes[1, 1].set_title("Overlay")

    axes[1, 2].imshow(ref_u8, cmap="gray")
    axes[1, 2].set_title("Reference (original)")

    for ax in axes.ravel():
        ax.grid(True, alpha=0.3)
    plt.suptitle(f"Manual tie-point alignment — {sample_name}  "
                 f"({n_inliers}/{n_used} inliers)", fontsize=10)
    plt.tight_layout()

    if save_path:
        fname = os.path.join(save_path, f"{sample_name}_LED_manual_alignment.pdf")
        fig.savefig(fname, dpi=300, facecolor="w")
        print(f"  Saved: {fname}")
    if show:
        plt.show()
    else:
        plt.close(fig)

    return M, aligned_tgt, n_used


# ──────────────────────────────────────────────
# 6. Apply a pre-computed affine matrix
# ──────────────────────────────────────────────

def apply_affine(array_2d, M, sample_name="alignment",
                 vmin=None, vmax=None, cmap="RdBu_r", units="nT",
                 pixel_size_um=None, save_path=None, show=True):
    """
    Warp a 2-D array (e.g. Bz) using a pre-computed affine matrix.

    Parameters
    ----------
    array_2d : ndarray (H, W)
        Data to transform (float).
    M : ndarray (2, 3)
        Affine matrix from compute_affine_matrix.
    sample_name : str
        Label for plots / filenames.
    vmin, vmax : float or None
        Colour limits for the QC plot.  If None, uses data min/max.
    cmap : str
        Matplotlib colourmap name.
    units : str
        Label for the colorbar.
    pixel_size_um : float or None
        QDM pixel size in micrometres.  If given, plot axes show um.
        Does not affect the saved data.
    save_path : str or None
        Directory to save the QC figure.
    show : bool
        Display inline.

    Returns
    -------
    transformed : ndarray (H, W)
        Aligned array.
    """
    if M is None:
        raise ValueError("Affine matrix is None — cannot apply transformation.")

    arr = array_2d.astype(np.float32)
    h, w = arr.shape[:2]

    transformed = cv2.warpAffine(
        arr, M, (w, h),
        flags=cv2.INTER_NEAREST,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0
    )

    # Colour limits — default to full data range
    if vmin is None:
        vmin = np.nanmin(arr)
    if vmax is None:
        vmax = np.nanmax(arr)

    # --- QC figure ---
    fig = plt.figure(figsize=(13, 8))
    gs = gridspec.GridSpec(2, 2, height_ratios=[3, 1])

    # Build extent in microns if pixel_size is given
    if pixel_size_um is not None:
        extent = [0, w * pixel_size_um, h * pixel_size_um, 0]
        axis_label = "Position (um)"
    else:
        extent = None
        axis_label = "Pixel"

    ax1 = fig.add_subplot(gs[0, 0])
    im1 = ax1.imshow(arr, cmap=cmap, vmin=vmin, vmax=vmax, extent=extent)
    ax1.set_title(f"Unaligned — {sample_name}", fontsize=9)
    ax1.set_xlabel(axis_label); ax1.set_ylabel(axis_label)
    plt.colorbar(im1, ax=ax1, shrink=0.4, label=units)

    ax2 = fig.add_subplot(gs[0, 1])
    im2 = ax2.imshow(transformed, cmap=cmap, vmin=vmin, vmax=vmax, extent=extent)
    ax2.set_title(f"Aligned — {sample_name}", fontsize=9)
    ax2.set_xlabel(axis_label); ax2.set_ylabel(axis_label)
    plt.colorbar(im2, ax=ax2, shrink=0.4, label=units)

    ax3 = fig.add_subplot(gs[1, 0])
    ax3.hist(arr.ravel(), bins=80, color="steelblue", alpha=0.7, edgecolor="k")
    ax3.set_xlabel(f"Intensity ({units})"); ax3.set_ylabel("Counts")
    ax3.set_title("Unaligned histogram", fontsize=9)
    ax3.set_yscale("log")

    ax4 = fig.add_subplot(gs[1, 1])
    ax4.hist(transformed.ravel(), bins=80, color="firebrick", alpha=0.7, edgecolor="k")
    ax4.set_xlabel(f"Intensity ({units})"); ax4.set_ylabel("Counts")
    ax4.set_title("Aligned histogram", fontsize=9)
    ax4.set_yscale("log")

    plt.tight_layout()
    if save_path:
        fname = os.path.join(save_path, f"{sample_name}_Bz_alignment.pdf")
        fig.savefig(fname, dpi=300, facecolor="w")
        print(f"  Saved: {fname}")
    if show:
        plt.show()
    else:
        plt.close(fig)

    print(f"  [{sample_name}] shape {arr.shape} -> {transformed.shape}  |  "
          f"min {transformed.min():.1f}  max {transformed.max():.1f}")

    return transformed


# ──────────────────────────────────────────────
# 7. Load field data (.mat / .npy / .csv)
# ──────────────────────────────────────────────

def load_field_data(path, mat_key="Bz", scale=1e9, flipud=True):
    """
    Load a 2-D field array from .mat, .npy, or .csv.

    Parameters
    ----------
    path : str
        File path.
    mat_key : str
        Variable name inside .mat files (default "Bz").
    scale : float
        Multiplicative scaling factor (default 1e9, i.e. T -> nT).
        Set to 1.0 if data is already in desired units.
    flipud : bool
        Flip array vertically (QDM convention).

    Returns
    -------
    ndarray (H, W)
    """
    ext = os.path.splitext(path)[1].lower()

    if ext == ".mat":
        data = sio.loadmat(path)[mat_key] * scale
    elif ext == ".npy":
        data = np.load(path) * scale
    elif ext in (".csv", ".tsv", ".txt"):
        data = np.loadtxt(path, delimiter=",") * scale
    else:
        raise ValueError(f"Unsupported format: {ext}")

    if flipud:
        data = np.flipud(data)

    return data.astype(np.float64)


# ──────────────────────────────────────────────
# 8. Save field data (.mat / .npy / .csv)
# ──────────────────────────────────────────────

def save_field_data(path, array, mat_key="Bz_aligned"):
    """
    Save a 2-D array to .mat, .npy, or .csv (inferred from extension).

    Parameters
    ----------
    path : str
        Output file path.
    array : ndarray
        Data to save.
    mat_key : str
        Variable name if saving as .mat.
    """
    ext = os.path.splitext(path)[1].lower()

    if ext == ".mat":
        sio.savemat(path, {mat_key: array})
    elif ext == ".npy":
        np.save(path, array)
    elif ext in (".csv", ".tsv", ".txt"):
        np.savetxt(path, array, delimiter=",")
    else:
        raise ValueError(f"Unsupported format: {ext}")

    print(f"  Saved: {path}")
