import React, { useState, useCallback, useEffect } from 'react';
import useWebSocket, { ReadyState } from 'react-use-websocket';
import { useParams } from 'react-router-dom';
import * as Progress from '@radix-ui/react-progress';
import { Container, Flex, Text, Card, Box } from "@radix-ui/themes";
import Background from "@/components/Background";
import StatusMessage from '../components/StatusMessage';
import Spinner from '../components/Spinner';
import Logo from "@/components/Logo";

type MessageType = {
    status: string,
    step: string,
    task_id: string,
    total_progress: number,
    payload?: {
        type?: 'file' | 'youtube',
        file_path?: string,
        url?: string
    },
    error?: string
};

function TaskStatusView() {
    let { taskId } = useParams();
    const socketUrl = `ws://localhost:8888/api/v1/task/${taskId}`;
    const [messageHistory, setMessageHistory] = useState<MessageEvent[]>([]);
    const [progress, setProgress] = React.useState(13);

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

    const lastMessageData: MessageType | null = lastMessage ? JSON.parse(lastMessage.data) : null;
    const totalProgress: number = lastMessageData?.total_progress || 0;

    return (
        <Background>
            <Container size="3" className="py-8">
                <Flex direction="column" align="center" gap="6">
                    <h1 className="text-2xl font-bold mb-8">meow</h1>
                    <h1 className="text-2xl font-bold">Task Status</h1>
                    <Logo isLoading={!lastMessage} />
                    
                    <Card size="2" className="card-container w-full max-w-2xl p-6">
                        <Flex direction="column" gap="4">
                            {!lastMessage && (
                                <div className="flex justify-center mb-4">
                                    <Spinner />
                                </div>
                            )}

                            <Text size="5" weight="bold">
                                Task ID: {taskId}
                            </Text>

                            <div className="space-y-4">
                                {lastMessageData?.error && (
                                    <Box className="mb-4 p-4 bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded-md">
                                        {lastMessageData.error}
                                    </Box>
                                )}

                                <div className="space-y-2">
                                    <Text size="4" weight="medium" className="block">
                                        Status: <span className={`${
                                            lastMessageData?.status === 'failed' ? 'text-red-500' : 'text-accent-9'
                                        }`}>{lastMessageData?.status}</span>
                                    </Text>
                                    <Text className="text-gray-500 block">
                                        Current Step: {lastMessageData?.step}
                                    </Text>
                                </div>

                                <div className="w-full">
                                    <Progress.Root
                                        className="relative overflow-hidden rounded-full w-full h-[25px] bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700"
                                        value={totalProgress}
                                        max={100}
                                    >
                                        <Progress.Indicator
                                            className="bg-accent-9 h-full transition-transform duration-[660ms] ease-[cubic-bezier(0.65, 0, 0.35, 1)]"
                                            style={{
                                                transform: `translateX(-${100 - (totalProgress || 0)}%)`
                                            }}
                                        />
                                    </Progress.Root>
                                    <Text className="mt-2">
                                        Progress: {totalProgress || 0}%
                                    </Text>
                                </div>

                                {lastMessageData?.status === 'finished' && lastMessageData?.payload && (
                                    <div className="mt-4">
                                        <a 
                                            href={lastMessageData.payload.type === 'youtube' 
                                                ? lastMessageData.payload.url 
                                                : `http://localhost:8888/api/v1/task/${taskId}/download/${lastMessageData.payload.file_path}`}
                                            className="text-accent-9 hover:text-accent-10 font-semibold text-lg transition-colors"
                                            target="_blank"
                                            rel="noopener noreferrer"
                                        >
                                            {lastMessageData.payload.type === 'youtube' 
                                                ? 'View on YouTube'
                                                : 'Download Processed Video'}
                                        </a>
                                    </div>
                                )}
                            </div>
                        </Flex>
                    </Card>
                </Flex>
            </Container>
        </Background>
    );
}

export default TaskStatusView;
