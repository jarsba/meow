from abc import ABC, abstractmethod
import cv2


class VideoMixerBase(ABC):

    @abstractmethod
    def mix_video(self, video_capture1: cv2.VideoCapture, video_capture2: cv2.VideoCapture, video_output_path: str) -> cv2.VideoWriter:
        pass
