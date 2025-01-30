import cv2
import numpy as np
from tqdm import tqdm

from .video_mixer_base import VideoMixerBase

class FarnebackOpticalFlowMixer(VideoMixerBase):

    def detect_action_hotspot(self, frame, prev_frame):
        """Detect where the action is happening based on player clusters and movement"""
        # Convert frames to grayscale for processing
        curr_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        
        # 1. Calculate motion using optical flow
        flow = cv2.calcOpticalFlowFarneback(
            prev_gray, curr_gray, None, 0.5, 3, 15, 3, 5, 1.2, 0
        )
        magnitude, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        
        # 2. Detect player clusters
        # Use simple threshold to detect players (assuming they contrast with field)
        _, player_mask = cv2.threshold(
            curr_gray, 
            np.mean(curr_gray) + np.std(curr_gray), 
            255, 
            cv2.THRESH_BINARY
        )
        
        # 3. Combine motion and player detection
        # Weight recent motion more heavily than static player positions
        motion_weight = 0.7
        player_weight = 0.3
        
        action_map = (motion_weight * magnitude + 
                    player_weight * player_mask.astype(float))
        
        # 4. Calculate center of action
        M = cv2.moments(action_map)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
        else:
            cx = frame.shape[1] // 2
            
        # Return normalized x-position of action center
        return cx / frame.shape[1]

    def mix_video(self, video_capture_left: cv2.VideoCapture,
                                        video_capture_right: cv2.VideoCapture,
                                        video_output_path: str,
                                        flow_fps=30,
                                        history_length=12,
                                        input_fps: int = 30,
                                        output_fps: int = 30,
                                        output_height: int = 1080,
                                        output_width: int = 1920,
                                        fourcc: cv2.VideoWriter_fourcc = cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'),
                                        progress_callback=None) -> cv2.VideoWriter:
            """
            Mix videos by tracking action center and switching between cameras.
            """
            if output_fps > input_fps:
                raise ValueError("Output fps cannot be higher than input fps")

            # Get total frames
            left_n_frames = int(video_capture_left.get(cv2.CAP_PROP_FRAME_COUNT)) - 1
            right_n_frames = int(video_capture_right.get(cv2.CAP_PROP_FRAME_COUNT)) - 1
            total_frames = min(left_n_frames, right_n_frames)

            # Initialize video writer
            video_output = cv2.VideoWriter(video_output_path, fourcc, output_fps, (output_width, output_height))

            # Initialize first frames
            _, first_left = video_capture_left.read()
            _, first_right = video_capture_right.read()
            
            if first_left is None or first_right is None:
                raise ValueError("Could not read first frames from videos")

            # Initialize tracking variables
            prev_frame_left = first_left
            prev_frame_right = first_right
            optical_flow_history = [0]  # Start with left camera
            frames_per_flow = max(1, round(input_fps / flow_fps))
            smoothed_score = 0.5  # Start in the middle
            
            # Write first frame
            video_output.write(first_left)
            
            logger.debug(f"Processing {total_frames} frames with flow calculation every {frames_per_flow} frames")

            # Process remaining frames
            for i in tqdm(range(1, total_frames)):
                res_left, frame_left = video_capture_left.read()
                res_right, frame_right = video_capture_right.read()

                if res_left is False or res_right is False:
                    break

                # Calculate action position on regular intervals
                if i % frames_per_flow == 0:
                    # Get action position for both cameras
                    left_action_pos = self.detect_action_hotspot(frame_left, prev_frame_left)
                    right_action_pos = self.detect_action_hotspot(frame_right, prev_frame_right)
                    
                    # Determine which camera has the action
                    # Assuming left camera covers left half, right camera covers right half
                    # Add overlap in the middle (0.4-0.6) to prevent rapid switching
                    use_left = (left_action_pos < 0.6 or  # Action clearly in left half
                            (right_action_pos < 0.4))   # Action not visible in right camera
                    
                    optical_flow_history.append(0 if use_left else 1)
                    if len(optical_flow_history) > history_length:
                        optical_flow_history = optical_flow_history[-history_length:]
                    
                    # Smooth transitions using exponential moving average
                    alpha = 0.7  # Smoothing factor
                    current_score = np.mean(optical_flow_history)
                    smoothed_score = alpha * current_score + (1 - alpha) * smoothed_score
                    
                    # Update previous frames for next iteration
                    prev_frame_left = frame_left
                    prev_frame_right = frame_right

                # Write frame based on smoothed history
                use_left = smoothed_score < 0.5
                video_output.write(frame_left if use_left else frame_right)

                # Handle frame rate conversion if needed
                if output_fps < input_fps and i % (input_fps // output_fps) != 0:
                    continue

                if progress_callback:
                    progress = int((i / total_frames) * 100)
                    progress_callback(progress)

            # Cleanup
            video_capture_left.release()
            video_capture_right.release()
            video_output.release()

            return video_output