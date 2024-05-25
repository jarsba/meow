from video_mixer_base import VideoMixerBase
from field_detector import mask_field_from_image
from optical_flow import absolute_difference_optical_flow
import cv2
from tqdm import tqdm
import numpy as np
import logging
import os
import tempfile

logger = logging.getLogger(__name__)


def prepare_frame(frame):
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    frame = cv2.GaussianBlur(frame, (9, 9), 0)
    return frame


def prepare_frame_with_mask(frame, mask):
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    frame = cv2.GaussianBlur(frame, (9, 9), 0)
    frame = cv2.bitwise_and(frame, frame, mask=mask)
    return frame


class AbsoluteDifferenceOpticalFlowMixer(VideoMixerBase):

    def mix_video(self, video_capture_left: cv2.VideoCapture, video_capture_right: cv2.VideoCapture,
                  video_output_path: str, flow_fps=5, history_length=24, output_fps: int = 60,
                  output_height: int = 1080, output_width: int = 1920,
                  fourcc: cv2.VideoWriter_fourcc = cv2.VideoWriter_fourcc('M', 'J', 'P', 'G')) -> cv2.VideoWriter:
        left_n_frames = int(video_capture_left.get(cv2.CAP_PROP_FRAME_COUNT)) - 1
        right_n_frames = int(video_capture_right.get(cv2.CAP_PROP_FRAME_COUNT)) - 1
        total_frames = min(left_n_frames, right_n_frames)

        video_output = cv2.VideoWriter(video_output_path, fourcc, output_fps, (output_width, output_height))

        prev_left = None
        prev_right = None

        # Denote 0 for left frame, 1 for right frame. Always write the frame that has more "wins" in the last 10 frames
        optical_flow_history = []

        for i in tqdm(range(total_frames)):

            res_left, frame_left = video_capture_left.read()
            res_right, frame_right = video_capture_right.read()

            if res_left is False or res_right is False:
                break

            if i == 0:
                masked_left = prepare_frame(frame_left)
                masked_right = prepare_frame(frame_right)

                prev_left = masked_left
                prev_right = masked_right
                continue

            if i < flow_fps:
                video_output.write(frame_left)
            elif i % flow_fps == 0:

                masked_left = prepare_frame(frame_left)
                masked_right = prepare_frame(frame_right)

                thresh_l = absolute_difference_optical_flow(prev_left, masked_left)
                thresh_r = absolute_difference_optical_flow(prev_right, masked_right)

                left_movement = np.sum(thresh_l)
                right_movement = np.sum(thresh_r)

                if left_movement >= right_movement:
                    optical_flow_history.append(0)
                else:
                    optical_flow_history.append(1)

                last_history = optical_flow_history[-history_length:]
                if np.mean(last_history) < 0.5:
                    video_output.write(frame_left)
                else:
                    video_output.write(frame_right)

            else:
                last_history = optical_flow_history[-history_length:]
                if np.mean(last_history) < 0.5:
                    video_output.write(frame_left)
                else:
                    video_output.write(frame_right)

            prev_left = masked_left
            prev_right = masked_right

        video_capture_left.release()
        video_capture_right.release()
        video_output.release()

        return video_output

    def mix_video_with_field_mask(self, video_capture_left: cv2.VideoCapture,
                                  video_capture_right: cv2.VideoCapture, video_output_path: str, flow_fps=5,
                                  history_length=24, input_fps: int = 30, output_fps: int = 30,
                                  output_height: int = 1080, output_width: int = 1920,
                                  fourcc: cv2.VideoWriter_fourcc = cv2.VideoWriter_fourcc('M', 'J', 'P',
                                                                                          'G')) -> cv2.VideoWriter:

        if output_fps > input_fps:
            raise ValueError("Output fps cannot be higher than input fps")

        left_n_frames = int(video_capture_left.get(cv2.CAP_PROP_FRAME_COUNT)) - 1
        right_n_frames = int(video_capture_right.get(cv2.CAP_PROP_FRAME_COUNT)) - 1
        total_frames = min(left_n_frames, right_n_frames)

        video_output = cv2.VideoWriter(video_output_path, fourcc, output_fps, (output_width, output_height))

        prev_left = None
        prev_right = None
        mask_left = None
        mask_right = None

        # Denote 0 for left frame, 1 for right frame. Always write the frame that has more "wins" in the last 10 frames
        optical_flow_history = []

        for i in tqdm(range(total_frames)):

            res_left, frame_left = video_capture_left.read()
            res_right, frame_right = video_capture_right.read()

            if res_left is False or res_right is False:
                break

            if i == 0:
                mask_left = mask_field_from_image(frame_left)
                mask_right = mask_field_from_image(frame_right)

                masked_left = prepare_frame_with_mask(frame_left, mask_left)
                masked_right = prepare_frame_with_mask(frame_right, mask_right)

                temp_dir = tempfile.gettempdir()
                cv2.imwrite(os.path.join(temp_dir, "mask_left.jpg"), masked_left)
                cv2.imwrite(os.path.join(temp_dir, "mask_right.jpg"), masked_right)

                logger.debug(f"Wrote mask file to {temp_dir}")

                prev_left = masked_left
                prev_right = masked_right
                continue

            # Write every flow_fps'th frame
            if i < flow_fps:
                video_output.write(frame_left)
            elif i % flow_fps == 0:

                masked_left = prepare_frame_with_mask(frame_left, mask_left)
                masked_right = prepare_frame_with_mask(frame_right, mask_right)

                thresh_l = absolute_difference_optical_flow(prev_left, masked_left)
                thresh_r = absolute_difference_optical_flow(prev_right, masked_right)

                left_movement = np.sum(thresh_l)
                right_movement = np.sum(thresh_r)

                if left_movement >= right_movement:
                    optical_flow_history.append(0)
                else:
                    optical_flow_history.append(1)

                last_history = optical_flow_history[-history_length:]
                if np.mean(last_history) < 0.5:
                    video_output.write(frame_left)
                else:
                    video_output.write(frame_right)

            else:
                last_history = optical_flow_history[-history_length:]
                if np.mean(last_history) < 0.5:
                    video_output.write(frame_left)
                else:
                    video_output.write(frame_right)

            prev_left = masked_left
            prev_right = masked_right

        video_capture_left.release()
        video_capture_right.release()
        video_output.release()

        return video_output
