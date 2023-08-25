import asyncio
from typing import Dict, List
from fastapi import WebSocket


class ConnectionManager:

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, task_id: str):
        await websocket.accept()
        if task_id in self.active_connections:
            self.active_connections.get(task_id).append(websocket)
        else:
            self.active_connections.update({task_id: [websocket]})

    def disconnect(self, websocket: WebSocket, task_id: str):
        self.active_connections.get(task_id).remove(websocket)
        if len(self.active_connections.get(task_id)) == 0:
            self.active_connections.pop(task_id)

    def send_message(self, data: dict, task_id: str):
        sockets = self.active_connections.get(task_id)
        if sockets:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            for socket in sockets:
                loop.run_until_complete(socket.send_json(data))


socket_connections = ConnectionManager()
