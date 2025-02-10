from typing import Mapping, List
import sys
import os

from .utils.video_utils import get_video_info, get_last_frame
import cv2
import numpy as np
from .logger import setup_logger

logger = setup_logger(__name__)


def calculate_video_file_linking(video_file_paths: List[str], similarity_threshold: float = 5) -> List:
    logger.info("Calculating video file links")

    # Trivial case: only one video
    if len(video_file_paths) == 1:
        return video_file_paths

    # Extract frames first
    frame_mapping = extract_end_frames(video_file_paths)
    
    # Calculate similarity matrix
    similarity_matrix = calculate_similarity_matrix(video_file_paths, frame_mapping)
    
    n_files = len(video_file_paths)

    # Find N-1 best matches (excluding diagonal and duplicates)
    matches = set()  # Use set to avoid duplicates
    for i in range(2 * n_files):
        for j in range(2 * n_files):
            # Skip diagonal elements and lower triangle
            if i//2 < j//2:  # Different files, upper triangle only
                matches.add((i, j, similarity_matrix[i][j]))
    
    # Sort by similarity score
    matches = sorted(matches, key=lambda x: x[2])
    best_matches = matches[:n_files-1]
    
    # Build video mapping from best matches
    video_end_to_start_mapping = {}
    for i, j, score in best_matches:
        # If comparing first frame of file i (i is even)
        # then file j's last frame matches file i's first frame
        # so the link should be from j to i
        if i % 2 == 0:
            file1 = video_file_paths[j//2]  # From file with matching last frame
            file2 = video_file_paths[i//2]  # To file with matching first frame
        # If comparing last frame of file i (i is odd)
        # then file i's last frame matches file j's first frame
        # so the link should be from i to j
        else:
            file1 = video_file_paths[i//2]  # From file with matching last frame
            file2 = video_file_paths[j//2]  # To file with matching first frame
            
        logger.debug(f"Best match: {os.path.basename(file1)} -> {os.path.basename(file2)} (score: {score:.4f})")
        add_edge(video_end_to_start_mapping, file1, file2)
    
    try:
        video_file_linking = find_linking(video_end_to_start_mapping)
        return video_file_linking
    except RuntimeError as e:
        logger.error("Failed to find valid video linking with best matches")
        raise


def extract_end_frames(video_file_paths: List[str]) -> Mapping:
    frame_mapping = {}

    for file_path in video_file_paths:

        video_info = get_video_info(file_path)
        duration = video_info['duration']

        capture = cv2.VideoCapture(file_path)

        # Read first frame
        capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret_first, first_frame = capture.read()

        # Read last frame
        ret_last, last_frame = get_last_frame(capture, duration)

        if ret_first is False or ret_last is False:
            logger.error(f"Failed to read frame from video {file_path}, first frame: {ret_first}, last frame: {ret_last}")

        frame_mapping[file_path] = {
            'first_frame': first_frame,
            'last_frame': last_frame
        }

        capture.release()

    return frame_mapping


def calculate_similarity_matrix(video_file_paths: List[str], frame_mapping: Mapping) -> List[List[float]]:
    # Build similarity matrix
    n_files = len(video_file_paths)
    similarity_matrix = [[0.0] * (2 * n_files) for _ in range(2 * n_files)]
    
    # Calculate similarities between all frames
    for i, file1 in enumerate(video_file_paths):
        frames1 = frame_mapping[file1]
        for j, file2 in enumerate(video_file_paths):
            frames2 = frame_mapping[file2]
            
            # Only calculate upper triangle to avoid duplicates
            if i < j:
                # Compare first frame of file1 to both frames of file2
                similarity_matrix[i*2][j*2] = calculate_frame_similarity(
                    frames1['first_frame'], frames2['first_frame'])
                similarity_matrix[i*2][j*2+1] = calculate_frame_similarity(
                    frames1['first_frame'], frames2['last_frame'])
                
                # Compare last frame of file1 to both frames of file2
                similarity_matrix[i*2+1][j*2] = calculate_frame_similarity(
                    frames1['last_frame'], frames2['first_frame'])
                similarity_matrix[i*2+1][j*2+1] = calculate_frame_similarity(
                    frames1['last_frame'], frames2['last_frame'])
                
                # Mirror the values to lower triangle
                similarity_matrix[j*2][i*2] = similarity_matrix[i*2][j*2]
                similarity_matrix[j*2][i*2+1] = similarity_matrix[i*2][j*2+1]
                similarity_matrix[j*2+1][i*2] = similarity_matrix[i*2+1][j*2]
                similarity_matrix[j*2+1][i*2+1] = similarity_matrix[i*2+1][j*2+1]

    return similarity_matrix


def calculate_frame_similarity(frame1, frame2):
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

    frame_height = gray1.shape[0]
    frame_width = gray1.shape[1]

    n_pixels = frame_height * frame_width

    diff_frame = cv2.absdiff(frame1, frame2)

    thresh_frame = cv2.threshold(src=diff_frame, thresh=50, maxval=255, type=cv2.THRESH_BINARY)[1]

    difference = np.sum(thresh_frame)
    difference_per_pixel = difference / n_pixels

    return difference_per_pixel


def add_edge(mapping, node1, node2):
    if node1 in mapping:
        mapping[node1].append(node2)
    else:
        mapping[node1] = [node2]


def find_linking(mapping) -> List[str]:
    valid_linking = check_linking_valid(mapping)
    if valid_linking is False:
        raise RuntimeError("Cannot find linked list for videos mapping")

    childs = [value[0] for value in mapping.values()]
    keys = list(mapping.keys())

    root_node = list(set(keys) - set(childs))[0]
    order = [root_node]

    next_node = None
    last_node = root_node
    for _ in range(len(mapping)):
        next_node = mapping[last_node][0]
        order.append(next_node)
        last_node = next_node

    return order


def check_linking_valid(mapping):
    """We want to check that
        a) there is only one root node
        b) the chain is not broken e.g. each node links to another node
        c) there is only one child node that doesn't exist in keys
        d) each node has exactly one parent except root node and each node has exactly one child
    """

    childs = [value[0] for value in mapping.values()]
    keys = list(mapping.keys())

    # a)
    root_nodes = list(set(keys) - set(childs))
    if len(root_nodes) != 1:
        return False

    # b)
    visited_nodes = []
    last_node = root_nodes[0]
    next_node = None
    for _ in range(len(mapping)):
        next_nodes = mapping[last_node]
        if len(next_nodes) != 1:
            logger.error("Cannot determine video linking")
            logger.debug(f"Video mapping: {mapping}")
            sys.exit(1)
        next_node = next_nodes[0]
        visited_nodes.append(next_node)
        last_node = next_node

    if len(visited_nodes) != len(mapping):
        return False

    # c)
    leafs = list(set(childs) - set(keys))
    if len(leafs) != 1:
        return False

    return True
