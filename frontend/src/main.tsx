import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import "./index.css"
import { TooltipProvider } from "@/components/ui/tooltip"
import App from "./App.tsx"

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <TooltipProvider delay={200}>
      <App />
    </TooltipProvider>
  </StrictMode>
)
