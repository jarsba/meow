from pathlib import Path
import os
from typing import Tuple


def format_filename(filename, extension):
    return f"{filename}.{extension}"


def extract_filename_without_extension(path) -> str:
    filename = Path(path).stem
    return filename


# Split file path from extension and convert file extension to lower case
def split_file_from_extension(path, without_dot=True) -> Tuple[str, str]:
    filename, extension = os.path.splitext(path)
    if without_dot:
        extension = extension.replace('.', '').lower()
    return filename, extension


def extract_folder_from_path(path) -> str:
    return os.path.dirname(path)


# Separate path to three parts: folder, filename, file extension
def separate_path_to_parts(path) -> Tuple[str, str, str]:
    filename = extract_filename_without_extension(path)
    file_extension = split_file_from_extension(path)[1]
    folder = extract_folder_from_path(path)

    return folder, filename, file_extension
