import ffmpeg
from utils import extract_filename_without_extension


def convert_to(video_path, target_file_type="mp4"):

    if original_file_type == target_file_type:
        raise ValueError(
            f"Conversion not supported between identical filetypes: {original_file_type} and {target_file_type}")

    stream = ffmpeg.input(video_path)
    filename = extract_filename_without_extension(video_path)
    stream = ffmpeg.output(stream, f'{filename}.{target_file_type}')
    ffmpeg.run(stream)
