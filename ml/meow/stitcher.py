
from stitcher_base import StitcherBase
import cv2
import logging


logger = logging.getLogger(__name__)


class Stitcher(StitcherBase):

    def stitch(self, video_capture_left: cv2.VideoCapture, video_capture_right: cv2.VideoCapture, output_path: str):
        pass
