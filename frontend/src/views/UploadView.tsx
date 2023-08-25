import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Input } from "@/components/input"
import { Label } from "@/components/label"
import { Button } from "@/components/button"
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/form"
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"


function App() {

  const [leftVideoFiles, setLeftVideoFiles] = useState<File[]>()
  const [rightVideoFiles, setRightVideoFiles] = useState<File[]>()
  const navigate = useNavigate();

  function onSubmit(event: any) {
    event.preventDefault();
    const formData = new FormData();

    interface videoMeta {
      'left_videos': string[],
      'right_videos': string[]
    }

    let metadata: videoMeta = {
      left_videos: [],
      right_videos: []
    };
    let leftFiles: string[] = [];
    let rightFiles: string[] = [];


    for (let file of (leftVideoFiles || [])) {
      formData.append(`files`, file, file.name);
      leftFiles.push(file.name);
    };

    for (let file of (rightVideoFiles || [])) {
      formData.append(`files`, file, file.name)
      rightFiles.push(file.name);
    };

    metadata['left_videos'] = leftFiles
    metadata['right_videos'] = rightFiles

    formData.append("metadata", JSON.stringify(metadata));

    const config = {
      headers: {
        'content-type': 'multipart/form-data',
      },
    };

    fetch('http://localhost:8000/api/v1/task', {
      method: 'POST',
      body: formData,
    })
    .then((res) => res.json())
    .then((data) => {
        console.log(data)
        const taskId = data['task_id']
        navigate(`/task/${taskId}`)
    })
    .catch((err) => console.error(err))
  };

  function handleLeftFilesChange(event: any) {
    setLeftVideoFiles(event.target.files)
  }

  function handleRightFilesChange(event: any) {
    setRightVideoFiles(event.target.files)
  }


  return <div className="App">
    <div className="container mx-auto p-20">
      <div className="flex flex-col justify-center text-center items-center">
        <h1>meow</h1>
        <form onSubmit={onSubmit}>
          <div className="flex flex-row">
            <div className="grid w-full max-w-sm items-center gap-1.5 m-8">
              <Label htmlFor="picture" className="my-5">Left camera video</Label>
              <input id="leftVideo" type="file" multiple onChange={handleLeftFilesChange} />
            </div>
            <div className="grid w-full max-w-sm items-center gap-1.5 m-8">
              <Label htmlFor="picture" className="my-5">Right camera video</Label>
              <input id="rightVideo" type="file" multiple onChange={handleRightFilesChange} />
            </div>
          </div>
          <Button type="submit">Submit</Button>
        </form>
      </div>
    </div >
  </div >;
}

export default App;
