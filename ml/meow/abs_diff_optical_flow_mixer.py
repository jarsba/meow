from .video_mixer_base import VideoMixerBase
from .field_detector import mask_field_from_image
from .optical_flow import absolute_difference_optical_flow
import cv2
from tqdm import tqdm
import numpy as np
import os
import tempfile
from .logger import setup_logger

logger = setup_logger(__name__)


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
                  fourcc: cv2.VideoWriter_fourcc = cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'),
                  progress_callback=None) -> cv2.VideoWriter:

        input_fps = int(video_capture_left.get(cv2.CAP_PROP_FPS))
        if output_fps > input_fps:
            raise ValueError("Output fps cannot be higher than input fps")

        left_n_frames = int(video_capture_left.get(cv2.CAP_PROP_FRAME_COUNT)) - 1
        right_n_frames = int(video_capture_right.get(cv2.CAP_PROP_FRAME_COUNT)) - 1
        total_frames = min(left_n_frames, right_n_frames)

        video_output = cv2.VideoWriter(video_output_path, fourcc, output_fps, (output_width, output_height))

        # Initialize first frames
        _, first_left = video_capture_left.read()
        _, first_right = video_capture_right.read()
        
        if first_left is None or first_right is None:
            raise ValueError("Could not read first frames from videos")

        prev_left = prepare_frame(first_left)
        prev_right = prepare_frame(first_right)
        
        # Write first frame
        video_output.write(first_left)
        
        optical_flow_history = [0]  # Start with left camera
        frames_per_flow = max(1, round(input_fps / flow_fps))  # How many frames between flow calculations
        
        logger.debug(f"Processing {total_frames} frames with flow calculation every {frames_per_flow} frames")

        # Process remaining frames
        for i in tqdm(range(1, total_frames)):
            res_left, frame_left = video_capture_left.read()
            res_right, frame_right = video_capture_right.read()

            if res_left is False or res_right is False:
                break

            # Calculate optical flow on regular intervals
            if i % frames_per_flow == 0:
                masked_left = prepare_frame(frame_left)
                masked_right = prepare_frame(frame_right)

                thresh_l = absolute_difference_optical_flow(prev_left, masked_left)
                thresh_r = absolute_difference_optical_flow(prev_right, masked_right)

                left_movement = np.sum(thresh_l)
                right_movement = np.sum(thresh_r)

                # Update history
                optical_flow_history.append(0 if left_movement >= right_movement else 1)
                if len(optical_flow_history) > history_length:
                    optical_flow_history = optical_flow_history[-history_length:]

                # Update previous frames for next flow calculation
                prev_left = masked_left
                prev_right = masked_right

            # Write frame based on recent history
            use_left = np.mean(optical_flow_history) < 0.5
            video_output.write(frame_left if use_left else frame_right)

            # Handle frame rate conversion if needed
            if output_fps < input_fps and i % (input_fps // output_fps) != 0:
                continue

            if progress_callback:
                progress = int((i / total_frames) * 100)
                progress_callback(progress)

        video_capture_left.release()
        video_capture_right.release()
        video_output.release()

        return video_output

    def mix_video_with_field_mask(self, video_capture_left: cv2.VideoCapture,
                                  video_capture_right: cv2.VideoCapture, video_output_path: str, flow_fps=5,
                                  history_length=24, input_fps: int = 30, output_fps: int = 30,
                                  output_height: int = 1080, output_width: int = 1920,
                                  fourcc: cv2.VideoWriter_fourcc = cv2.VideoWriter_fourcc('M', 'J', 'P','G'),
                                  progress_callback=None) -> cv2.VideoWriter:

        if output_fps > input_fps:
            raise ValueError("Output fps cannot be higher than input fps")

        left_n_frames = int(video_capture_left.get(cv2.CAP_PROP_FRAME_COUNT)) - 1
        right_n_frames = int(video_capture_right.get(cv2.CAP_PROP_FRAME_COUNT)) - 1
        total_frames = min(left_n_frames, right_n_frames)

        video_output = cv2.VideoWriter(video_output_path, fourcc, output_fps, (output_width, output_height))

        # Initialize masks and previous frames
        _, first_left = video_capture_left.read()
        _, first_right = video_capture_right.read()
        
        if first_left is None or first_right is None:
            raise ValueError("Could not read first frames from videos")

        mask_left = mask_field_from_image(first_left)
        mask_right = mask_field_from_image(first_right)
        
        prev_left = prepare_frame_with_mask(first_left, mask_left)
        prev_right = prepare_frame_with_mask(first_right, mask_right)
        
        # Write first frame
        video_output.write(first_left)
        
        optical_flow_history = [0]  # Start with left camera
        frames_per_flow = max(1, round(input_fps / flow_fps))  # How many frames between flow calculations
        
        logger.debug(f"Processing {total_frames} frames with flow calculation every {frames_per_flow} frames")

        # Process remaining frames
        for i in tqdm(range(1, total_frames)):
            res_left, frame_left = video_capture_left.read()
            res_right, frame_right = video_capture_right.read()

            logger.debug(f"Processing frame {i}")

            # Calculate optical flow on regular intervals
            if i % frames_per_flow == 0:
                masked_left = prepare_frame_with_mask(frame_left, mask_left)
                masked_right = prepare_frame_with_mask(frame_right, mask_right)

                thresh_l = absolute_difference_optical_flow(prev_left, masked_left)
                thresh_r = absolute_difference_optical_flow(prev_right, masked_right)

                left_movement = np.sum(thresh_l)
                right_movement = np.sum(thresh_r)

                # Update history
                optical_flow_history.append(0 if left_movement >= right_movement else 1)
                if len(optical_flow_history) > history_length:
                    optical_flow_history = optical_flow_history[-history_length:]

                # Update previous frames for next flow calculation
                prev_left = masked_left
                prev_right = masked_right

            # Write frame based on recent history
            use_left = np.mean(optical_flow_history) < 0.5
            video_output.write(frame_left if use_left else frame_right)

            # Handle frame rate conversion if needed
            if output_fps < input_fps and i % (input_fps // output_fps) != 0:
                continue

            if progress_callback:
                progress = int((i / total_frames) * 100)
                progress_callback(progress)

        video_capture_left.release()
        video_capture_right.release()
        video_output.release()

        return video_output

