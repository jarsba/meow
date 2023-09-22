import * as React from "react"

type MessageType = {
    status: string,
    step: string,
    task_id: string,
    step_progress: number,
    total_progress: number,
};

interface StatusMessageProps {
    idx: number,
    message: MessageType,
}

const StatusMessage: React.FC<StatusMessageProps> = ({ idx, message }): JSX.Element => {
    
    return (
        <>
            <div key={idx} className="max-w-sm p-6 bg-white border border-gray-200 rounded-lg shadow dark:bg-gray-800 dark:border-gray-700">
                <p>Status: {message.status}</p>
                <p>Step: {message.step}</p>
                <p>Step progress: {message.step_progress}</p>
                <p>Total progress: {message.total_progress}</p>
            </div>
        </>
    );
}

export default StatusMessage
