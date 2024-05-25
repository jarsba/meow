import os
from moviepy.Clip import Clip
from moviepy.tools import subprocess_call
from moviepy.config import get_setting
from utils.video_utils import get_video_info
from moviepy.video.io.VideoFileClip import VideoFileClip
import logging

logger = logging.getLogger(__name__)


def ffmpeg_extract_subclip(filename, t1, t2, targetname=None):
    """ Makes a new video file playing video file ``filename`` between
    the times ``t1`` and ``t2``. """
    name, ext = os.path.splitext(filename)
    if not targetname:
        T1, T2 = [int(1000 * t) for t in [t1, t2]]
        targetname = "%sSUB%d_%d.%s" % (name, T1, T2, ext)

    cmd = [get_setting("FFMPEG_BINARY"), "-y",
           "-ss", "%0.2f" % t1,
           "-i", filename,
           "-t", "%0.2f" % (t2 - t1),
           "-vcodec", "copy", "-acodec", "copy", targetname]

    subprocess_call(cmd)


def extract_subclip(input_video_path, start_time, end_time) -> VideoFileClip:
    video = VideoFileClip(input_video_path)
    subclip: VideoFileClip = video.subclip(start_time, end_time)
    return subclip


# If delay is positive, audio1 needs to be delayed and negative if audio2 needs to be delayed
def synchronize_videos(video1_path: str, video2_path: str, delay: float, video1_output_path: str, video2_output_path: str):
    video1_info = get_video_info(video1_path)
    video2_info = get_video_info(video2_path)

    assert video1_info['frame_rate'] == video2_info['frame_rate']

    final_duration = min(video1_info['duration'], video2_info['duration']) - abs(delay)

    if delay >= 0:
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
