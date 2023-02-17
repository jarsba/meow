import numpy as np
import cv2

def lukas_kanade_optical_flow(frame1: np.ndarray, frame2: np.ndarray) -> np.ndarray:
    features = cv2