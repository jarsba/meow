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
import { Theme, ThemePanel } from "@radix-ui/themes";
import "@radix-ui/themes/styles.css";

const rootElement = document.getElementById("root");
const root = createRoot(rootElement!);

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
    <Theme
      appearance="light"
      accentColor="blue"
      grayColor="slate"
      radius="medium"
      scaling="100%"
      hasBackground
    >
      <RouterProvider router={router} />
      <ThemePanel />
    </Theme>
  </React.StrictMode>
);
