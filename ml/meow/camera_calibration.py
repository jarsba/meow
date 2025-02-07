import cv2
import numpy as np
import glob
from typing import Tuple, Union
from .logger import setup_logger

logger = setup_logger(__name__)

def calibrate_camera(calibration_image_path: str, checkerboard_size: Tuple[int, int] = (7, 9), image_type: str = "jpg") -> Union[Tuple, None]:
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

    images = glob.glob(f"{calibration_image_path}/*.{image_type}")

    three_d_points = []
    two_d_points = []

    objectp3d = np.zeros((1, checkerboard_size[0] * checkerboard_size[1], 3), np.float32)
    objectp3d[0, :, :2] = np.mgrid[0:checkerboard_size[0], 0:checkerboard_size[1]].T.reshape(-1, 2)
    img_shape = cv2.imread(images[0]).shape[0:2]

    for filename in images:
        image = cv2.imread(filename)
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Find the chess board corners
        # If desired number of corners are
        # found in the image then ret = true
        ret, corners = cv2.findChessboardCorners(gray_image, checkerboard_size,
                                                 cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_FAST_CHECK + cv2.CALIB_CB_NORMALIZE_IMAGE)
        # If desired number of corners can be detected then,
        # refine the pixel coordinates and display
        # them on the images of checkerboard
        if ret is True:
            three_d_points.append(objectp3d)
            # Refining pixel coordinates
            # for given 2d points.
            corners2 = cv2.cornerSubPix(gray_image, corners, (11, 11), (-1, -1), criteria)
            two_d_points.append(corners2)
        else:
            logger.warning(f"Pattern was not found on image {filename}")

    ret, matrix, distortion, r_vecs, t_vecs = cv2.calibrateCamera(
        three_d_points, two_d_points, img_shape[::-1], None, None
    )

    if ret is True:
        return matrix, distortion, r_vecs, t_vecs
    else:
        logger.warning(f"Camera calibration failed")
        return None
