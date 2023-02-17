import cv2

class Stitcher:
    def __init__(self, input_path_1: str, input_path_2: str, output: str = "output.mp4"):
        self.input_path_1 = input_path_1
        self.input_path_2 = input_path_2
        self.output = output

    @staticmethod
    def read_stream(self, input_path: str):
        capture = cv2.VideoCapture(input_path)
        return capture

    def stitch(self, video_stream_1, video_stream_2, output="output.mp4"):
        # TODO: finish
        pass

    def save_output(self):
        # TODO: finish
        pass
