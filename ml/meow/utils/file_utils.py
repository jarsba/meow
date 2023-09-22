from pathlib import Path
import os
from typing import Tuple
from .string_utils import generate_random_string

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


def create_temporary_file_name_with_extension(base_folder, extension) -> str:
    """Creates temporary file with random name and given extension in base folder and returns its path"""
    filename = f"{generate_random_string()}.{extension}"
    file_path = os.path.join(base_folder, filename)
    return file_path
