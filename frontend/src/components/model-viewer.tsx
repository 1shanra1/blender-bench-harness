import { useEffect, useRef, useState, useCallback } from "react"
import * as THREE from "three"
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js"
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js"
import { Box, Image as ImageIcon, RotateCcw } from "lucide-react"
import { AspectRatio } from "@/components/ui/aspect-ratio"
import { Skeleton } from "@/components/ui/skeleton"
import { Empty, EmptyMedia, EmptyTitle } from "@/components/ui/empty"

type AxisKey = "positive_x" | "negative_x" | "positive_y" | "negative_y" | "positive_z" | "negative_z"

const AXIS_DIRECTIONS: Record<AxisKey, [number, number, number]> = {
  positive_x: [1, 0, 0],
  negative_x: [-1, 0, 0],
  positive_y: [0, 1, 0.0001],
  negative_y: [0, -1, 0.0001],
  positive_z: [0, 0, 1],
  negative_z: [0, 0, -1],
}

const AXIS_LABELS: [AxisKey, string][] = [
  ["positive_x", "+X"],
  ["negative_x", "−X"],
  ["positive_y", "+Y"],
  ["negative_y", "−Y"],
  ["positive_z", "+Z"],
  ["negative_z", "−Z"],
]

export function ModelViewer({
  modelUrl,
  renderUrl,
  label,
  ratio = 1.33,
  onOpenRender,
}: {
  modelUrl: string | null
  renderUrl: string | null
  label: string
  ratio?: number
  onOpenRender?: () => void
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [loadedUrl, setLoadedUrl] = useState<string | null>(null)
  const [failedUrl, setFailedUrl] = useState<string | null>(null)
  const [showRender, setShowRender] = useState(false)
  const [activeAxis, setActiveAxis] = useState<AxisKey | null>(null)

  const loading = Boolean(modelUrl && !showRender && loadedUrl !== modelUrl && failedUrl !== modelUrl)
  const error = Boolean(modelUrl && failedUrl === modelUrl)

  const controlsRef = useRef<OrbitControls | null>(null)
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null)
  const initialCamPos = useRef<THREE.Vector3>(new THREE.Vector3())
  const initialTarget = useRef<THREE.Vector3>(new THREE.Vector3())
  const modelRadiusRef = useRef<number>(1)
  const requestRef = useRef<number>(0)

  useEffect(() => {
    if (!modelUrl || showRender) {
      return
    }

    const container = containerRef.current
    if (!container) return

    // Scene
    const scene = new THREE.Scene()

    // Camera
    const width = container.clientWidth || 300
    const height = container.clientHeight || 200
    const camera = new THREE.PerspectiveCamera(40, width / height, 0.01, 1000)
    cameraRef.current = camera

    // Renderer
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: "high-performance",
    })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setSize(width, height)
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.1
    renderer.outputColorSpace = THREE.SRGBColorSpace

    const canvas = renderer.domElement
    canvas.style.width = "100%"
    canvas.style.height = "100%"
    canvas.style.display = "block"
    container.replaceChildren(canvas)

    // Controls
    const controls = new OrbitControls(camera, canvas)
    controls.enableDamping = true
    controls.dampingFactor = 0.08
    controls.rotateSpeed = 0.8
    controls.zoomSpeed = 0.9
    controls.enablePan = true
    controlsRef.current = controls

    // Lighting (studio 3-point lighting setup)
    const ambientLight = new THREE.AmbientLight(0xffffff, 1.2)
    scene.add(ambientLight)

    const keyLight = new THREE.DirectionalLight(0xffffff, 2.2)
    keyLight.position.set(3, 4, 3)
    scene.add(keyLight)

    const fillLight = new THREE.DirectionalLight(0xb5bccb, 1.1)
    fillLight.position.set(-3, 1, 2)
    scene.add(fillLight)

    const rimLight = new THREE.DirectionalLight(0x9ca3af, 1.4)
    rimLight.position.set(0, -3, -3)
    scene.add(rimLight)

    const topLight = new THREE.DirectionalLight(0xffffff, 0.8)
    topLight.position.set(0, 5, 0)
    scene.add(topLight)

    // Load Model
    const loader = new GLTFLoader()
    let disposed = false

    loader.load(
      modelUrl,
      (gltf) => {
        if (disposed) return
        const model = gltf.scene

        // Calculate bounding box and center
        const box = new THREE.Box3().setFromObject(model)
        const center = box.getCenter(new THREE.Vector3())
        const size = box.getSize(new THREE.Vector3())
        const maxDim = Math.max(size.x, size.y, size.z)
        const radius = Math.max(maxDim / 2, 0.001)
        modelRadiusRef.current = radius

        // Center model geometry at (0, 0, 0)
        model.position.x = -center.x
        model.position.y = -center.y
        model.position.z = -center.z
        scene.add(model)

        // Position camera to fit object cleanly in view
        const fov = camera.fov * (Math.PI / 180)
        const distance = (radius * 1.6) / Math.sin(fov / 2)
        const camPos = new THREE.Vector3(distance * 0.7, distance * 0.45, distance * 0.8)
        camera.position.copy(camPos)
        camera.lookAt(0, 0, 0)
        camera.near = distance * 0.01
        camera.far = distance * 10
        camera.updateProjectionMatrix()

        controls.target.set(0, 0, 0)
        controls.minDistance = distance * 0.3
        controls.maxDistance = distance * 4
        controls.update()

        initialCamPos.current.copy(camPos)
        initialTarget.current.set(0, 0, 0)

        setLoadedUrl(modelUrl)
      },
      undefined,
      () => {
        if (!disposed) {
          setFailedUrl(modelUrl)
        }
      }
    )

    // Render loop
    const animate = () => {
      requestRef.current = requestAnimationFrame(animate)
      controls.update()
      renderer.render(scene, camera)
    }
    requestRef.current = requestAnimationFrame(animate)

    // Resize handling
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const w = entry.contentRect.width
        const h = entry.contentRect.height
        if (w > 0 && h > 0) {
          camera.aspect = w / h
          camera.updateProjectionMatrix()
          renderer.setSize(w, h)
        }
      }
    })
    resizeObserver.observe(container)

    return () => {
      disposed = true
      cancelAnimationFrame(requestRef.current)
      resizeObserver.disconnect()
      controls.dispose()
      renderer.dispose()
      scene.clear()
      if (container.contains(canvas)) {
        container.removeChild(canvas)
      }
    }
  }, [modelUrl, showRender])

  // Snap to specific axis view
  const snapToAxis = useCallback((axis: AxisKey) => {
    const controls = controlsRef.current
    const camera = cameraRef.current
    if (!controls || !camera) return

    setActiveAxis(axis)
    const dir = AXIS_DIRECTIONS[axis]
    const distance = initialCamPos.current.length()
    const target = controls.target

    camera.position.set(
      target.x + dir[0] * distance,
      target.y + dir[1] * distance,
      target.z + dir[2] * distance
    )
    camera.lookAt(target)
    controls.update()
  }, [])

  // Reset to original isometric camera view
  const resetCamera = useCallback(() => {
    const controls = controlsRef.current
    const camera = cameraRef.current
    if (!controls || !camera) return

    setActiveAxis(null)
    camera.position.copy(initialCamPos.current)
    controls.target.copy(initialTarget.current)
    controls.update()
  }, [])

  return (
    <AspectRatio ratio={ratio} className="image-frame relative group">
      {/* 3D Model Viewport */}
      {modelUrl && !error && !showRender ? (
        <div className="relative w-full h-full">
          {loading && (
            <Skeleton className="absolute inset-0 rounded-none z-10" />
          )}
          <div
            ref={containerRef}
            className="w-full h-full cursor-grab active:cursor-grabbing"
            aria-label={`Interactive 3D model: ${label}`}
          />

          {/* Floating Controls Overlay */}
          <div className="model-controls">
            <div className="model-axis-bar" role="toolbar" aria-label="Camera snap views">
              {AXIS_LABELS.map(([key, title]) => (
                <button
                  key={key}
                  type="button"
                  className={`axis-chip ${activeAxis === key ? "active" : ""}`}
                  onClick={() => snapToAxis(key)}
                  aria-label={`View from ${title}`}
                >
                  {title}
                </button>
              ))}
              <span className="axis-divider" />
              <button
                type="button"
                className="axis-chip icon-chip"
                onClick={resetCamera}
                aria-label="Reset camera"
                title="Reset view"
              >
                <RotateCcw size={11} />
              </button>
              {renderUrl && (
                <button
                  type="button"
                  className="axis-chip icon-chip"
                  onClick={() => setShowRender(true)}
                  aria-label="View 2D render"
                  title="View Cycles render"
                >
                  <ImageIcon size={11} />
                </button>
              )}
            </div>
          </div>
        </div>
      ) : showRender && renderUrl ? (
        /* Fallback / 2D Render view */
        <div className="relative w-full h-full">
          <button
            type="button"
            className="image-button"
            onClick={onOpenRender}
            aria-label={`Enlarge render: ${label}`}
          >
            <img src={renderUrl} alt={label} className="w-full h-full object-cover" />
          </button>
          {modelUrl && !error && (
            <div className="model-controls">
              <button
                type="button"
                className="axis-chip text-chip"
                onClick={() => setShowRender(false)}
                aria-label="Switch back to 3D model"
              >
                <Box size={11} />
                <span>3D Model</span>
              </button>
            </div>
          )}
        </div>
      ) : renderUrl ? (
        /* Run has 2D render but no 3D model */
        <button
          type="button"
          className="image-button"
          onClick={onOpenRender}
          aria-label={`Enlarge render: ${label}`}
        >
          <img src={renderUrl} alt={label} className="w-full h-full object-cover" />
        </button>
      ) : (
        /* Failed / No render available */
        <Empty className="absolute inset-0 gap-2 p-4">
          <EmptyMedia>
            <Box size={24} strokeWidth={1.3} />
          </EmptyMedia>
          <EmptyTitle className="font-normal text-muted-foreground">
            {error ? "3D model unavailable" : "No final model"}
          </EmptyTitle>
        </Empty>
      )}
    </AspectRatio>
  )
}
