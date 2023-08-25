from fastapi import APIRouter, BackgroundTasks, UploadFile, Form, HTTPException, WebSocket, WebSocketDisconnect
import typing as t
from typing import Annotated
import json
import uuid
from connection_manager import socket_connections
from enum import Enum
from time import sleep
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class TaskStatus(str, Enum):
    STARTED = 'STARTED'
    RUNNING = 'RUNNING'
    FINISHED = 'FINISHED'


class TaskUpdate(t.TypedDict):
    status: t.Literal[TaskStatus.STARTED, TaskStatus.RUNNING, TaskStatus.FINISHED]
    step: str
    step_progress: int
    total_progress: int
    task_id: str


def analyze_video(left_videos: t.List[UploadFile], right_videos: t.List[UploadFile], task_id: str):
    sleep(10)
    logger.info(f"Sending status message to client {task_id}")
    #message: TaskUpdate = TaskUpdate(status=TaskStatus.STARTED, step="Sorting videos", task_id=task_id, step_progress=0,
    #                                 total_progress=0)

    message = {
        'status': 'started',
        'step': 'Sorting videos',
        'task_id': task_id,
        'step_progress': 0,
        'total_progress': 0
    }
    socket_connections.send_message(message, task_id=task_id)

    logger.info(f"Status sent to client {task_id}")

    logger.info(f"Sending status message to client {task_id}")

    message = {
        'status': 'started',
        'step': 'Concating videos',
        'task_id': task_id,
        'step_progress': 0,
        'total_progress': 10
    }
    socket_connections.send_message(message, task_id=task_id)

    logger.info(f"Status sent to client {task_id}")


@router.post(
    "/task",
    response_model=t.Mapping,
    response_model_exclude_none=True,
)
async def create_new_task(files: list[UploadFile], metadata: Annotated[str, Form()], background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    metadata = json.loads(metadata)
    left_videos_names = metadata['left_videos']
    right_videos_names = metadata['right_videos']

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

    background_tasks.add_task(analyze_video, left_videos=left_videos, right_videos=right_videos, task_id=task_id)

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
