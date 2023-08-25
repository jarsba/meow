
from src.stitcher_base import StitcherBase
import os
from statistics import median
import sys
import cv2
import matplotlib.pyplot as plt
import numpy as np
import logging
from src.stitching_utils import resize_images, DEFAULT_LOW_MEGAPIX, DEFAULT_MEDIUM_MEGAPIX, DEFAULT_FINAL_MEGAPIX

from stitching.image_handler import ImageHandler
from stitching.feature_detector import FeatureDetector
from stitching.feature_matcher import FeatureMatcher
from stitching.subsetter import Subsetter
from stitching.camera_estimator import CameraEstimator
from stitching.camera_adjuster import CameraAdjuster
from stitching.camera_wave_corrector import WaveCorrector
from stitching.warper import Warper
from stitching.cropper import Cropper
from stitching.seam_finder import SeamFinder
from stitching.exposure_error_compensator import ExposureErrorCompensator
from stitching.blender import Blender

logger = logging.getLogger(__name__)


class Stitcher(StitcherBase):

    def stitch(self, video_capture_left: cv2.VideoCapture, video_capture_right: cv2.VideoCapture, output_path: str):

        # TODO: make loop for all frames
        res_left, frame_left = video_capture_left.read()
        res_right, frame_right = video_capture_right.read()

        images = [frame_left, frame_right]

        medium_images = resize_images(images, scale=DEFAULT_MEDIUM_MEGAPIX)
        low_images = resize_images(medium_images, scale=DEFAULT_LOW_MEGAPIX)
        final_images = resize_images(images, scale=DEFAULT_FINAL_MEGAPIX)

        finder = cv2.SIFT_create()
        features = [cv2.detail.computeImageFeatures2(finder, img) for img in medium_images]

        matcher = cv2.detail_BestOf2NearestMatcher()
        matches = matcher.apply2(features)
        matcher.collectGarbage()

        camera_estimator = cv2.detail_HomographyBasedEstimator()
        b, cameras = self.estimator.apply(features, matches, None)
        if not b:
            logger.error("Homography estimation failed.")
            sys.exit(1)
        for cam in cameras:
            cam.R = cam.R.astype(np.float32)

        camera_adjuster = cv2.detail_BundleAdjusterRay()
        b, cameras = camera_adjuster.apply(features, matches, cameras)
        if not b:
            logger.error("Camera parameters adjusting failed.")
            sys.exit(1)

        wave_corrector = cv2.detail.WAVE_CORRECT_HORIZ()
        rmats = [np.copy(cam.R) for cam in cameras]
        rmats = cv2.detail.waveCorrect(rmats, wave_corrector)
        for idx, cam in enumerate(cameras):
            cam.R = rmats[idx]

        warper = cv2.PyRotationWarper("mercator", self.scale * aspect)


        focals = [cam.focal for cam in cameras]
        scale = median(focals)

        low_sizes = img_handler.get_low_img_sizes()
        camera_aspect = img_handler.get_medium_to_low_ratio()  # since cameras were obtained on medium imgs

        warped_low_images = []

        for image, camera in zip(low_imgs, cameras):
            _, warped_image = warper.warp(
                image,
                Warper.get_K(camera, aspect),
                camera.R,
                cv2.INTER_LINEAR,
                cv2.BORDER_REFLECT,
            )

            warped_low_images.append(warped_image)


        warped_low_imgs = list(warper.warp_images(low_imgs, cameras, camera_aspect))
        warped_low_masks = list(warper.create_and_warp_masks(low_sizes, cameras, camera_aspect))
        low_corners, low_sizes = warper.warp_rois(low_sizes, cameras, camera_aspect)

        final_sizes = img_handler.get_final_img_sizes()
        camera_aspect = img_handler.get_medium_to_final_ratio()  # since cameras were obtained on medium imgs

        warped_final_imgs = list(warper.warp_images(final_imgs, cameras, camera_aspect))
        warped_final_masks = list(warper.create_and_warp_masks(final_sizes, cameras, camera_aspect))
        final_corners, final_sizes = warper.warp_rois(final_sizes, cameras, camera_aspect)

        cropper = Cropper()

        low_corners = cropper.get_zero_center_corners(low_corners)

        cropper.prepare(warped_low_imgs, warped_low_masks, low_corners, low_sizes)

        cropped_low_masks = list(cropper.crop_images(warped_low_masks))
        cropped_low_imgs = list(cropper.crop_images(warped_low_imgs))
        low_corners, low_sizes = cropper.crop_rois(low_corners, low_sizes)

        lir_aspect = img_handler.get_low_to_final_ratio()
        cropped_final_masks = list(cropper.crop_images(warped_final_masks, lir_aspect))
        cropped_final_imgs = list(cropper.crop_images(warped_final_imgs, lir_aspect))
        final_corners, final_sizes = cropper.crop_rois(final_corners, final_sizes, lir_aspect)

        seam_finder = SeamFinder(finder="dp_color")

        seam_masks = seam_finder.find(cropped_low_imgs, low_corners, cropped_low_masks)
        seam_masks = [seam_finder.resize(seam_mask, mask) for seam_mask, mask in zip(seam_masks, cropped_final_masks)]

        compensator = ExposureErrorCompensator()

        compensator.feed(low_corners, cropped_low_imgs, cropped_low_masks)

        compensated_imgs = [compensator.apply(idx, corner, img, mask)
                            for idx, (img, mask, corner)
                            in enumerate(zip(cropped_final_imgs, cropped_final_masks, final_corners))]

        blender = Blender()
        blender.prepare(final_corners, final_sizes)
        for img, mask, corner in zip(compensated_imgs, seam_masks, final_corners):
            blender.feed(img, mask, corner)
        panorama, _ = blender.blend()
