from .utils.video_utils import get_video_info, ffmpeg_extract_subclip, get_video_info
from .utils.file_utils import create_temporary_file_name_with_extension
from typing import Optional
from .logger import setup_logger

logger = setup_logger(__name__)

# If delay is positive, audio1 needs to be delayed and negative if audio2 needs to be delayed
def synchronize_videos(video1_path: str, video2_path: str, delay: float, video1_output_path: Optional[str] = None, video2_output_path: Optional[str] = None, temp_dir: Optional[str] = None, output_file_type: Optional[str] = None):
    """Delay is calculated based on video1 relative position to video2. If delay is positive, video1 is playing delay
    amount of time before video2 and video1 needs to delayed, meaning that we need to cut delay amount of time from the
    start of video1. If delay is negative, we need to do opposite."""

    logger.debug("Starting video synchronization")

    if video1_output_path is None:
        video1_output_path = create_temporary_file_name_with_extension(temp_dir, output_file_type)

    if video2_output_path is None:
        video2_output_path = create_temporary_file_name_with_extension(temp_dir, output_file_type)

    video1_info = get_video_info(video1_path)
    video2_info = get_video_info(video2_path)

    assert video1_info['frame_rate'] == video2_info['frame_rate']

    final_duration = min(video1_info['duration'], video2_info['duration']) - abs(delay)

    if delay > 0:
        logger.debug(f"Delay {video1_path} by {delay} seconds")

        video1_start_time = delay
        video1_end_time = final_duration + delay
        video2_start_time = 0
        video2_end_time = final_duration

        ffmpeg_extract_subclip(video1_path, video1_start_time, video1_end_time, video1_output_path)
        ffmpeg_extract_subclip(video2_path, video2_start_time, video2_end_time, video2_output_path)

    else:
        delay = abs(delay)
        logger.debug(f"Delay {video2_path} by {delay} seconds")

        video1_start_time = 0
        video1_end_time = final_duration
        video2_start_time = delay
        video2_end_time = final_duration + delay

        ffmpeg_extract_subclip(video1_path, video1_start_time, video1_end_time, video1_output_path)
        ffmpeg_extract_subclip(video2_path, video2_start_time, video2_end_time, video2_output_path)

    return video1_output_path, video2_output_path
