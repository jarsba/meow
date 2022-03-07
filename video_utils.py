from typing import Tuple

import ffmpeg
import ast
from utils import eval_expr


def get_frame_info(video_path) -> Tuple[int, int, int]:
    probe = ffmpeg.probe(video_path)
    video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
    width = int(video_stream['width'])
    height = int(video_stream['height'])
    frame_rate = round(eval_expr(video_stream['avg_frame_rate']))

    return height, width, frame_rate

