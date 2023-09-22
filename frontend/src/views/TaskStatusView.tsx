import React, { useState, useCallback, useEffect } from 'react';
import useWebSocket, { ReadyState } from 'react-use-websocket';
import { useParams } from 'react-router-dom';

import * as Progress from '@radix-ui/react-progress';

import StatusMessage from '../components/StatusMessage';
import Spinner from '../components/Spinner';


type MessageType = {
    status: string,
    step: string,
    task_id: string,
    step_progress: number,
    total_progress: number,
};

function TaskStatusView() {
    let { taskId } = useParams();
    const socketUrl = `ws://localhost:8000/api/v1/task/${taskId}`;
    const [messageHistory, setMessageHistory] = useState<MessageEvent[]>([]);
    const [progress, setProgress] = React.useState(13);


    const { lastMessage, readyState } = useWebSocket(socketUrl, {
        share: true,
    });


    useEffect(() => {
        const timer = setTimeout(() => setProgress(66), 500);
        return () => clearTimeout(timer);
    }, []);



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

    const lastMessageData: MessageType | null = lastMessage ? JSON.parse(lastMessage.data) : null
    const totalProgress: number = lastMessageData?.total_progress || 0

    console.log(lastMessageData)
    console.log(totalProgress)

    return (
        <div>
            {lastMessage === null ?
                <Spinner />
                : null
            }

            <h1 className="text-center">Status for {taskId}</h1>

            <div className="p-4 space-y-4">
                <div className="text-2xl font-bold">Status: {lastMessageData?.status} </div>
                <div className="text-lg">Step {lastMessageData?.step}</div>

                <Progress.Root
                    className="relative overflow-hidden rounded-full w-[300px] h-[25px] bg-gray-200"
                    style={{ transform: 'translateZ(0)', }}
                    value={totalProgress}
                >
                    <Progress.Indicator
                        className="bg-green-500 w-full h-full transition-transform duration-[660ms] ease-[cubic-bezier(0.65, 0, 0.35, 1)]"
                        style={{ transform: `translateX(-${100 - totalProgress}%)` }}
                    />
                </Progress.Root>


                {lastMessageData?.status === 'finished' && (
                    <div className="text-3xl font-bold text-blue-500">
                        <a href="#">Your Task URL</a>
                    </div>
                )}
            </div>

        </div>
    );
};

export default TaskStatusView;
