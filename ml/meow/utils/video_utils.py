from typing import Dict, Union, List

from .eval_utils import eval_expr

from tempfile import NamedTemporaryFile
import ffmpeg
from moviepy.video.VideoClip import VideoClip
from moviepy.editor import VideoFileClip, concatenate_videoclips
import cv2


def get_video_info(video_path) -> Dict[str, Union[int, float, str]]:
    """
    Return JSON representing video info:
        file path
        frame width in pixels
        frame high in pixels
        frame rate as FPS
        duration in seconds
    """
    probe = ffmpeg.probe(video_path)
    file_path = str(probe['format']['filename'])
    video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
    width = int(video_stream['width'])
    height = int(video_stream['height'])
    frame_rate = round(eval_expr(video_stream['avg_frame_rate']))
    duration = float(probe['format']['duration'])

    return {
        "file_path": file_path,
        "frame_height": height,
        "frame_width": width,
        "frame_rate": frame_rate,
        "duration": duration
    }


def concatenate_video_clips(video_file_paths) -> VideoClip:
    clips = [VideoFileClip(file) for file in video_file_paths]
    final_clip = concatenate_videoclips(clips)
    return final_clip


def ffmpeg_concatenate_video_clips(video_file_paths: List[str], output_path: str):
    merged_video_list_file = NamedTemporaryFile(suffix=".txt")

    with open(merged_video_list_file.name, 'w') as f:
        for video in video_file_paths:
            f.write(f"file {video}\n")

    merged_video_list_file.seek(0)

    ffmpeg.input(merged_video_list_file.name,
                 format='concat', safe=0).output(output_path, codec='copy').run()


def get_last_frame(capture, duration):
    # Dirty hack to get to last 2 seconds to avoid reading to whole video file
    capture.set(cv2.CAP_PROP_POS_MSEC, (duration - 2) * 1000)
    last_frame = None
    while True:
        ret, tmp_frame = capture.read()
        if not ret:
            break
        last_frame = tmp_frame

    success = last_frame is not None
    return success, last_frame