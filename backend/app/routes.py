from fastapi import APIRouter, BackgroundTasks, UploadFile, Form, HTTPException, WebSocket, WebSocketDisconnect
import typing as t
import os
from typing import Annotated, Callable
import json
import uuid
from connection_manager import socket_connections
from enum import Enum
from time import sleep
import logging
from functools import partial
from ml.meow.meow import run_with_args
from fastapi.responses import FileResponse

logger = logging.getLogger(__name__)
router = APIRouter()

class TaskStatus(str, Enum):
    STARTED = 'started'
    FINISHED = 'finished'
    FAILED = 'failed'

def send_status_update(task_id: str, status: TaskStatus, step: str, total_progress: int, payload: dict = None, error: str = None):
    message = {
        'status': status.value,
        'step': step,
        'task_id': task_id,
        'total_progress': total_progress
    }
    if payload:
        message['payload'] = payload
    if error:
        message['error'] = error
    socket_connections.send_message(message, task_id=task_id)
    logger.info(f"Status update sent to client {task_id}: {message}")


def analyze_video(left_videos: t.List[UploadFile], right_videos: t.List[UploadFile], task_id: str,
                 video_processing_type: str = "panoramaStitching", output_fps: int = 30, 
                 start_time: float = None, end_time: float = None, upload_to_youtube: bool = False, youtube_title: str = "Meow Match Video"):
    try:
        # Initial status update
        send_status_update(task_id, TaskStatus.STARTED, "Preparing videos", 0)

        # Save uploaded files temporarily
        left_paths = []
        right_paths = []
        

        temp_dir_for_left_videos = f"/tmp/left_{task_id}"
        temp_dir_for_right_videos = f"/tmp/right_{task_id}"
        os.makedirs(temp_dir_for_left_videos, exist_ok=True)
        os.makedirs(temp_dir_for_right_videos, exist_ok=True)

        for i, video in enumerate(left_videos):
            path = f"{temp_dir_for_left_videos}/left_{i}.mp4"
            with open(path, "wb") as f:
                f.write(video.file.read())
            left_paths.append(path)
            
        for i, video in enumerate(right_videos):
            path = f"{temp_dir_for_right_videos}/right_{i}.mp4"
            with open(path, "wb") as f:
                f.write(video.file.read())
            right_paths.append(path)

        send_status_update(task_id, TaskStatus.FINISHED, "Preparing videos", 5)

        if start_time == 0:
            start_time = None
        if end_time == 0:
            end_time = None

        if video_processing_type == "panoramaStitching":
            use_mixer = False
            use_panorama_stitching = True
        else:
            use_mixer = True
            use_panorama_stitching = False

        send_status_update(task_id, TaskStatus.STARTED, "Processing videos", 5)

        # Call the actual processing function with progress callback
        def progress_callback(step: str, status: TaskStatus, total_progress: int, error: str = None):
            send_status_update(task_id, status, step, total_progress, error=error)

        # Run the video processing
        output_result = run_with_args(
            left_videos=left_paths,
            right_videos=right_paths,
            use_mixer=use_mixer,
            use_panorama_stitching=use_panorama_stitching,
            output_fps=output_fps,
            start_time=start_time,
            end_time=end_time,
            progress_callback=progress_callback,
            youtube_title=youtube_title
        )

        # Final status update with payload
        send_status_update(
            task_id, 
            TaskStatus.FINISHED, 
            "Processing videos", 
            100,
            payload=output_result  # This will include type, file_path, and url if it's YouTube
        )
                    
    except Exception as e:
        logger.error(f"Error processing task {task_id}: {str(e)}")
        send_status_update(task_id, TaskStatus.FAILED, "Error", 0, error=str(e))
        raise

@router.post("/task")
async def create_new_task(files: list[UploadFile], metadata: Annotated[str, Form()], background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    metadata = json.loads(metadata)
    left_videos_names = metadata['left_videos']
    right_videos_names = metadata['right_videos']
    settings = metadata["settings"]

    left_videos = []
    right_videos = []

    for file in files:

        if file.filename in left_videos_names:
            left_videos.append(file)
        elif file.filename in right_videos_names:
            right_videos.append(file)
        else:
            logger.error(f"Could not determine video channel source: {file.filename}")
            raise HTTPException(status_code=400, detail=f"Could not determine video channel source for file {file.filename}")

    video_processing_type = settings["videoProcessingType"]
    output_fps = settings["videoOutputFps"]
    start_time = settings["startTime"]
    end_time = settings["endTime"]
    upload_to_youtube = settings["uploadToYoutube"]
    youtube_title = settings["youtubeTitle"]
    background_tasks.add_task(analyze_video, left_videos=left_videos, right_videos=right_videos, task_id=task_id,
                              video_processing_type=video_processing_type, output_fps=output_fps, start_time=start_time,
                              end_time=end_time, upload_to_youtube=upload_to_youtube, youtube_title=youtube_title)

    response = {'task_id': task_id}
    return response


@router.websocket("/task/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    await socket_connections.connect(websocket, task_id=task_id)
    try:
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        socket_connections.disconnect(websocket, task_id=task_id)

@router.get("/task/{task_id}/download/{file_path:path}")
async def download_file(task_id: str, file_path: str):
    return FileResponse(
        path=file_path,
        filename="processed_video.mp4",
        media_type="video/mp4"
    )
