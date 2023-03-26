from abc import ABC, abstractmethod
import cv2


class StitcherBase(ABC):

    @abstractmethod
    def stitch(self, video_capture_left: cv2.VideoCapture, video_capture_right: cv2.VideoCapture,
               video_output_path: str):
        pass
