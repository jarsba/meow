import numpy as np
import cv2


def is_grayscale(frame: np.ndarray) -> bool:
    if len(frame.shape) < 3 or frame.shape[2] == 1:
        return True
    return False


def farneback_optical_flow(frame1: np.ndarray, frame2: np.ndarray) -> np.ndarray:
    if not is_grayscale(frame1):
        frame1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)

    if not is_grayscale(frame2):
        frame2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

    flow = cv2.calcOpticalFlowFarneback(
        frame1, frame2, None,
        pyr_scale=0.5,
        levels=5,
        winsize=15,
        iterations=5,
        poly_n=5,
        poly_sigma=1.2,
        flags=0
    )

    return flow


def absolute_difference_optical_flow(frame1, frame2):
    diff_frame = cv2.absdiff(frame1, frame2)

    kernel = np.ones((5, 5))
    diff_frame = cv2.dilate(diff_frame, kernel, 1)

    thresh_frame = cv2.threshold(src=diff_frame, thresh=30, maxval=255, type=cv2.THRESH_BINARY)[1]
    return thresh_frame


def calculate_flow_metric(flow):
    gray_mask = cv2.cvtColor(flow, cv2.COLOR_BGR2GRAY)
    blurred_mask = cv2.GaussianBlur(gray_mask, (3, 3), 0)
    mask_sum = np.sum(blurred_mask)

    return mask_sum