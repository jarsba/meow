import React from "react";
import { createRoot } from "react-dom/client";
import {
  createBrowserRouter,
  RouterProvider,
} from "react-router-dom";
import "./index.css";
import UploadView from "./views/UploadView";
import ErrorPage from "./views/ErrorPage";
import TaskStatusView from "./views/TaskStatusView";

const rootElement = document.getElementById("root");
const root = createRoot(rootElement!); // eslint-disable-line

const router = createBrowserRouter([
  {
    path: "/",
    element: <UploadView />,
    errorElement: <ErrorPage />,
  },
  {
    path: "task/:taskId",
    element: <TaskStatusView />,
  },
]);

root.render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
);
