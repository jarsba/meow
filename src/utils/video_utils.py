from typing import Tuple, Dict, Union, Any

import ffmpeg
from eval_utils import eval_expr


def get_video_info(video_path) -> Dict[str, Union[int, float, str]]:
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