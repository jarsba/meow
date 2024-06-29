from typing import Mapping, List

from utils.video_utils import get_video_info, get_last_frame
import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)


def calculate_video_file_linking(video_file_paths: List[str], similarity_threshold: float = 10) -> List:
    frame_mapping = extract_end_frames(video_file_paths)
    similarity_matrix = calculate_similarity_matrix(frame_mapping)

    video_end_to_start_mapping = {}

    for key, values in similarity_matrix.items():
        key1 = key[0]
        key2 = key[1]
        value1 = values[0]
        value2 = values[1]

        if value1 < similarity_threshold:
            add_edge(video_end_to_start_mapping, key2, key1)
        if value2 < similarity_threshold:
            add_edge(video_end_to_start_mapping, key1, key2)

    video_file_linking = find_linking(video_end_to_start_mapping)

    return video_file_linking


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


def calculate_similarity_matrix(frame_mapping: Mapping) -> Mapping:
    similarity_matrix = {}

    for i, pair1 in enumerate(frame_mapping.items()):
        for j, pair2 in enumerate(frame_mapping.items()):
            if i < j:
                key1, values1 = pair1
                key2, values2 = pair2

                first_vs_last = calculate_frame_similarity(values1['first_frame'], values2['last_frame'])
                last_vs_first = calculate_frame_similarity(values1['last_frame'], values2['first_frame'])

                similarity_matrix[(key1, key2)] = [first_vs_last, last_vs_first]

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


def find_linking(mapping):
    valid_linking = check_linking_valid(mapping)
    if valid_linking is False:
        logger.warning("Cannot find linked list for videos mapping")
        return None

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
        assert len(next_nodes) == 1
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
