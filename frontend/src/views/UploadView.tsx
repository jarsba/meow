import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Input } from "@/components/input"
import { Button } from "@/components/button"
import Spinner from "../components/Spinner";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/form"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/accordion"
import { Checkbox } from "@/components/checkbox"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/select"
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import Logo from "@/components/Logo";
import { Container, Flex, Box, Text, Card } from "@radix-ui/themes";
import Background from "@/components/Background";

const formSchema = z.object({
  settings: z.object({
    videoProcessingType: z.enum(["panoramaStitching", "opticalFlowMixer"]).default("panoramaStitching"),
    videoOutputFps: z.number().min(30.0).max(60.0).default(30.0),
    startTime: z.string().regex(/^(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d$/, "Please enter time in HH:MM:SS format").transform(timeToSeconds),
    endTime: z.string().regex(/^(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d$/, "Please enter time in HH:MM:SS format").transform(timeToSeconds),
    uploadToYoutube: z.boolean().default(false),
    youtubeTitle: z.string().optional(),
    burnLogo: z.boolean().default(false),
  })
})

// Helper function to convert HH:MM:SS to seconds
function timeToSeconds(time: string): number {
  const [hours, minutes, seconds] = time.split(':').map(Number);
  return (hours * 3600) + (minutes * 60) + seconds;
}

function App() {
  const [loading, setLoading] = useState<boolean>(false)
  const [leftVideoFiles, setLeftVideoFiles] = useState<File[]>()
  const [rightVideoFiles, setRightVideoFiles] = useState<File[]>()
  const navigate = useNavigate();

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      settings: {
        videoProcessingType: "panoramaStitching",
        videoOutputFps: 30.0,
        startTime: "00:00:00",
        endTime: "00:00:00",
        uploadToYoutube: false,
        youtubeTitle: "",
        burnLogo: false,
      },
    },
  })

  function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);

    const formData = new FormData();
    const rawSettings = form.getValues().settings;
    
    const settings = {
      ...rawSettings,
      startTime: timeToSeconds(rawSettings.startTime),
      endTime: timeToSeconds(rawSettings.endTime)
    };

    interface videoMeta {
      left_videos: string[],
      right_videos: string[],
      settings: typeof settings
    }

    let metadata: videoMeta = {
      left_videos: [],
      right_videos: [],
      settings: settings
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

    metadata.left_videos = leftFiles;
    metadata.right_videos = rightFiles;

    formData.append("metadata", JSON.stringify(metadata));

    fetch('http://localhost:8888/api/v1/task', {
      method: 'POST',
      body: formData,
      credentials: 'include',
      headers: {
        'Accept': 'application/json',
      },
    })
      .then((res) => res.json())
      .then((data) => {
        console.log(data)
        const taskId = data['task_id']
        navigate(`/task/${taskId}`)
      })
      .catch((err) => console.error(err))
  };

  function handleLeftFilesChange(event: React.ChangeEvent<HTMLInputElement>) {
    if (event.target.files) {
      setLeftVideoFiles(Array.from(event.target.files))
    }
  }

  function handleRightFilesChange(event: React.ChangeEvent<HTMLInputElement>) {
    if (event.target.files) {
      setRightVideoFiles(Array.from(event.target.files))
    }
  }

  return (
    <Background>
      <Container size="3" className="py-8">
        {loading && <Spinner />}
        <Flex direction="column" align="center" gap="6">
          <h1 className="text-2xl font-bold">meow</h1>
          <Logo isLoading={loading} />
          
          <Form {...form}>
            <Card size="2" className="card-container w-full max-w-2xl p-6">
              <form onSubmit={onSubmit}>
                <Flex direction="column" gap="6">
                  <Flex gap="6" direction="row">
                    <Box style={{ flex: 1 }}>
                      <Flex direction="column" align="center" gap="2">
                        <Text as="label" size="2" weight="bold" align="center">
                          Left Camera Video
                        </Text>
                        <Input 
                          type="file" 
                          multiple 
                          onChange={handleLeftFilesChange}
                          className="styled-input"
                        />
                      </Flex>
                    </Box>

                    <Box style={{ flex: 1 }}>
                      <Flex direction="column" align="center" gap="2">
                        <Text as="label" size="2" weight="bold" align="center">
                          Right Camera Video
                        </Text>
                        <Input 
                          type="file" 
                          multiple 
                          onChange={handleRightFilesChange}
                          className="styled-input"
                        />
                      </Flex>
                    </Box>
                  </Flex>

                  <Accordion type="single" collapsible className="w-full">
                    <AccordionItem value="settings">
                      <AccordionTrigger className="text-sm text-gray-600 hover:text-blue-600">
                        Advanced Settings
                      </AccordionTrigger>
                      <AccordionContent className="space-y-4">
                        <FormField
                          control={form.control}
                          name="settings.videoProcessingType"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel className="rt-Text">Processing Type</FormLabel>
                              <Select onValueChange={field.onChange} defaultValue={field.value}>
                                <FormControl>
                                  <SelectTrigger className="styled-input">
                                    <SelectValue placeholder="Select a processing type" />
                                  </SelectTrigger>
                                </FormControl>
                                <SelectContent>
                                  <SelectItem value="panoramaStitching">Panorama Stitching</SelectItem>
                                  <SelectItem value="opticalFlowMixer">Optical Flow Mixer</SelectItem>
                                </SelectContent>
                              </Select>
                            </FormItem>
                          )}
                        />
                        <FormField
                          control={form.control}
                          name="settings.videoOutputFps"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel className="rt-Text">Video Output FPS</FormLabel>
                              <FormControl>
                                <Input 
                                  type="number"
                                  className="styled-input"
                                  {...field} 
                                  onChange={e => field.onChange(Number(e.target.value))}
                                />
                              </FormControl>
                            </FormItem>
                          )}
                        />
                        <FormField
                          control={form.control}
                          name="settings.startTime"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel className="rt-Text">Start Time (HH:MM:SS)</FormLabel>
                              <FormControl>
                                <Input 
                                  type="text"
                                  pattern="^(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d$"
                                  placeholder="00:00:00"
                                  className="styled-input"
                                  {...field}
                                />
                              </FormControl>
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                        <FormField
                          control={form.control}
                          name="settings.endTime"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel className="rt-Text">End Time (HH:MM:SS)</FormLabel>
                              <FormControl>
                                <Input 
                                  type="text"
                                  pattern="^(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d$"
                                  placeholder="00:00:00"
                                  className="styled-input"
                                  {...field}
                                />
                              </FormControl>
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                        <FormField
                          control={form.control}
                          name="settings.uploadToYoutube"
                          render={({ field }) => (
                            <FormItem className="flex items-center space-x-2">
                              <FormControl>
                                <Checkbox 
                                  checked={field.value}
                                  onCheckedChange={field.onChange}
                                  className="styled-checkbox"
                                />
                              </FormControl>
                              <FormLabel className="rt-Text !mt-0">Upload to YouTube</FormLabel>
                            </FormItem>
                          )}
                        />
                        {form.watch("settings.uploadToYoutube") && (
                          <FormField
                            control={form.control}
                            name="settings.youtubeTitle"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel className="rt-Text">YouTube Title</FormLabel>
                                <FormControl>
                                  <Input 
                                    type="text"
                                    placeholder="Enter video title"
                                    className="styled-input"
                                    {...field}
                                  />
                                </FormControl>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
                        )}
                        <FormField
                          control={form.control}
                          name="settings.burnLogo"
                          render={({ field }) => (
                            <FormItem className="flex items-center space-x-2">
                              <FormControl>
                                <Checkbox 
                                  checked={field.value}
                                  onCheckedChange={field.onChange}
                                  className="styled-checkbox"
                                />
                              </FormControl>
                              <FormLabel className="rt-Text !mt-0">Burn Logo</FormLabel>
                            </FormItem>
                          )}
                        />
                      </AccordionContent>
                    </AccordionItem>
                  </Accordion>

                  <Button 
                    type="submit" 
                    className="styled-button w-full text-white"
                  >
                    Process Videos
                  </Button>
                </Flex>
              </form>
            </Card>
          </Form>
        </Flex>
      </Container>
    </Background>
  );
}

export default App;
