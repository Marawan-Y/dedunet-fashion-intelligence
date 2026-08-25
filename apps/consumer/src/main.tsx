import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./app/router";
import "./design-system/index.css";

const root = document.getElementById("root");
if (!root) throw new Error("#root is missing from index.html");

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
