import React from "react";
import { createRoot, hydrateRoot } from "react-dom/client";
import "@/index.css";
import App from "@/App";

const rootEl = document.getElementById("root");
const tree = (
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// Pre-rendered HTML has children in #root → hydrate; otherwise mount from scratch.
// `data-prerendered` is the attribute our postbuild script sets to disambiguate
// an empty CRA shell from a snapshotted page (CRA leaves #root with no children,
// but any future tooling that injects a loading spinner would also leave children).
if (rootEl.hasAttribute("data-prerendered") || rootEl.hasChildNodes()) {
  hydrateRoot(rootEl, tree);
} else {
  createRoot(rootEl).render(tree);
}
