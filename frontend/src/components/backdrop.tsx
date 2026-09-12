import { memo } from "react"
import { GrainGradient } from "@paper-design/shaders-react"

export default memo(function Backdrop() {
  return (
    <div className="shader-backdrop" aria-hidden="true">
      <GrainGradient
        speed={0}
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
})
