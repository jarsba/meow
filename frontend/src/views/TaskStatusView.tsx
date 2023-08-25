import React, { useState, useCallback, useEffect } from 'react';
import useWebSocket, { ReadyState } from 'react-use-websocket';

import { useParams } from 'react-router-dom';


function TaskStatusView() {
    let { taskId } = useParams();
    const socketUrl = `ws://localhost:8000/api/v1/task/${taskId}`;
    const [messageHistory, setMessageHistory] = useState<MessageEvent[]>([]);

    const { lastMessage, readyState } = useWebSocket(socketUrl, {
        share: true,
      });

    useEffect(() => {
        if (lastMessage !== null) {
            setMessageHistory((prev) => prev.concat(lastMessage));
        }
    }, [lastMessage, setMessageHistory]);

    const connectionStatus = {
        [ReadyState.CONNECTING]: 'Connecting',
        [ReadyState.OPEN]: 'Open',
        [ReadyState.CLOSING]: 'Closing',
        [ReadyState.CLOSED]: 'Closed',
        [ReadyState.UNINSTANTIATED]: 'Uninstantiated',
    }[readyState];

    return (
        <div>
            <span>The WebSocket is currently {connectionStatus}</span>
            {lastMessage ? <span>Last message: {lastMessage.data}</span> : null}
            <ul>
                {messageHistory.map((message, idx) => (
                    <span key={idx}>{message ? message.data : null}</span>
                ))}
            </ul>
        </div>
    );
};

export default TaskStatusView;
