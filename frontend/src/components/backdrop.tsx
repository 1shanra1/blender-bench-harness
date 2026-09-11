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
        softness={0.85}
        intensity={0.15}
        noise={0.12}
        shape="wave"
        frame={20729}
        colors={["#7300FF", "#EBA8FF", "#00BFFF", "#22112244"]}
        colorBack="#00000000"
        maxPixelCount={240000}
        style={{
          width: "100%",
          height: "100%",
          filter: "grayscale(100%) brightness(12%)",
          opacity: 0.65,
        }}
      />
    </div>
  )
}
