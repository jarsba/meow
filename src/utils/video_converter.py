import os
import ffmpeg
from eval_utils import extract_filename_without_extension, split_file_from_extension, extract_folder_from_path


def convert_to_type(video_path, output_path=None, target_file_type="mp4"):
    original_file_type = split_file_from_extension(video_path)[1]
    if output_path is None:
        output_path = extract_folder_from_path(video_path)

    if original_file_type == target_file_type:
        raise ValueError(
            f"Conversion not supported between identical filetypes: {original_file_type} and {target_file_type}")

    stream = ffmpeg.input(video_path)
    filename = extract_filename_without_extension(video_path)
    stream = ffmpeg.output(stream, os.path.join(output_path, f'{filename}.{target_file_type}'))
    ffmpeg.run(stream)
