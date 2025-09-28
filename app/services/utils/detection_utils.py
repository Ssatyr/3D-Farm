import cv2
import numpy as np


def detect_stringing(gray_image: np.ndarray) -> float:
    """Detect stringing by looking for thin diagonal lines."""
    edges = cv2.Canny(gray_image, 50, 150)
    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180, threshold=50, minLineLength=30, maxLineGap=10
    )
    if lines is None:
        return 0.0

    diagonal_lines = 0
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        if 15 < abs(angle) < 165:
            diagonal_lines += 1

    height, width = gray_image.shape
    stringing_ratio = diagonal_lines / (height * width / 10000)
    return float(min(stringing_ratio, 1.0))


def detect_layer_separation(gray_image: np.ndarray) -> float:
    """Detect layer separation by analyzing horizontal patterns."""
    horizontal_kernel = np.array([[-1, -1, -1], [2, 2, 2], [-1, -1, -1]])
    horizontal_edges = cv2.filter2D(gray_image, -1, horizontal_kernel)
    lines = cv2.HoughLinesP(
        horizontal_edges, 1, np.pi / 180, threshold=30, minLineLength=50, maxLineGap=5
    )
    if lines is None:
        return 0.0

    horizontal_line_count = len(lines)
    height, _ = gray_image.shape
    separation_ratio = horizontal_line_count / (height / 100)
    return float(min(separation_ratio, 1.0))


def detect_warping(gray_image: np.ndarray) -> float:
    """Detect warping by analyzing edge curvature and circularity deviation."""
    edges = cv2.Canny(gray_image, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return 0.0

    largest = max(contours, key=cv2.contourArea)
    perimeter = cv2.arcLength(largest, True)
    area = cv2.contourArea(largest)
    if area <= 0 or perimeter <= 0:
        return 0.0

    circularity = 4 * np.pi * area / (perimeter * perimeter)
    warping_score = 1.0 - circularity
    return float(min(max(warping_score, 0.0), 1.0))


def detect_blobs(gray_image: np.ndarray) -> float:
    """Detect blobs/overextrusion using simple blob detection."""
    params = cv2.SimpleBlobDetector_Params()
    params.filterByArea = True
    params.minArea = 100
    params.maxArea = 10000
    params.filterByCircularity = True
    params.minCircularity = 0.3

    detector = cv2.SimpleBlobDetector_create(params)
    keypoints = detector.detect(gray_image)
    if not keypoints:
        return 0.0

    blob_count = len(keypoints)
    height, width = gray_image.shape
    blob_ratio = blob_count / (height * width / 10000)
    return float(min(blob_ratio, 1.0))
