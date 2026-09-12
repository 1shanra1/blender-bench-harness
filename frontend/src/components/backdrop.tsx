import { useSyncExternalStore } from "react"
import { GrainGradient } from "@paper-design/shaders-react"

const query = "(prefers-reduced-motion: reduce)"
function subscribe(callback: () => void) {
  const media = window.matchMedia(query)
  media.addEventListener("change", callback)
  document.addEventListener("visibilitychange", callback)
  return () => {
    media.removeEventListener("change", callback)
    document.removeEventListener("visibilitychange", callback)
  }
}

export default function Backdrop() {
  const animate = useSyncExternalStore(
    subscribe,
    () =>
      !window.matchMedia(query).matches &&
      document.visibilityState === "visible",
    () => false
  )
  return (
    <div className="shader-backdrop" aria-hidden="true">
      <GrainGradient
        speed={animate ? 0.08 : 0}
        scale={0.3}
        offsetX={0.25}
        offsetY={0.4}
        softness={0.82}
        intensity={0.32}
        noise={0.1}
        shape="wave"
        frame={20729}
        colors={["#f87171", "#b91c1c", "#2563eb", "#38bdf8"]}
        colorBack="#00000000"
        maxPixelCount={240000}
        style={{
          width: "100%",
          height: "100%",
          opacity: 0.38,
        }}
      />
    </div>
  )
}
