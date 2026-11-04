import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "../../shared/theme.css";
import KindergartenDesign from "./KindergartenDesign";
import "./design.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <KindergartenDesign />
  </StrictMode>,
);
