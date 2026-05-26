# Copyright 2026 smart-ebocr Contributors
# SPDX-License-Identifier: Apache-2.0

"""Image preprocessing utilities for OCR."""

import os


def _check_cv2():
    try:
        import cv2
        return cv2
    except ImportError:
        raise ImportError("opencv-python 未安装。请运行: pip install opencv-python-headless")


def load_image(file_path):
    """Load image from file path."""
    cv2 = _check_cv2()
    return cv2.imread(file_path)


def enhance_for_ocr(img):
    """Apply preprocessing to improve OCR accuracy."""
    cv2 = _check_cv2()
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Apply adaptive thresholding
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )

    # Denoise
    denoised = cv2.fastNlMeansDenoising(binary, None, 10, 7, 21)

    return denoised


def save_processed(original_path, processed_img):
    """Save processed image and return new path."""
    cv2 = _check_cv2()
    base, ext = os.path.splitext(original_path)
    processed_path = f"{base}_processed{ext}"
    cv2.imwrite(processed_path, processed_img)
    return processed_path