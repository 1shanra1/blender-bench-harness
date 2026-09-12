import { useEffect, useRef, useState, useCallback } from "react"
import * as THREE from "three"
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js"
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js"
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js"
import { Box, Image as ImageIcon, RotateCcw } from "lucide-react"
import { AspectRatio } from "@/components/ui/aspect-ratio"
import { Empty, EmptyMedia, EmptyTitle } from "@/components/ui/empty"


function disposeModel(model: THREE.Object3D) {
  const textures = new Set<THREE.Texture>()
  model.traverse((object) => {
    if (!(object instanceof THREE.Mesh)) return
    object.geometry.dispose()
    const materials = Array.isArray(object.material) ? object.material : [object.material]
    for (const material of materials) {
      for (const value of Object.values(material)) {
        if (value instanceof THREE.Texture) textures.add(value)
      }
      material.dispose()
    }
  })
  textures.forEach((texture) => texture.dispose())
}

export function ModelViewer({
  modelUrl,
  renderUrl,
  label,
  ratio = 1.33,
  fillContainer = false,
  onOpenRender,
}: {
  modelUrl: string | null
  renderUrl: string | null
  label: string
  ratio?: number
  fillContainer?: boolean
  onOpenRender?: () => void
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [loadedUrl, setLoadedUrl] = useState<string | null>(null)
  const [failedUrl, setFailedUrl] = useState<string | null>(null)
  const [showRender, setShowRender] = useState(false)

  const loading = Boolean(modelUrl && !showRender && loadedUrl !== modelUrl && failedUrl !== modelUrl)
  const error = Boolean(modelUrl && failedUrl === modelUrl)

  const controlsRef = useRef<OrbitControls | null>(null)
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null)
  const initialCamPos = useRef<THREE.Vector3>(new THREE.Vector3())
  const initialTarget = useRef<THREE.Vector3>(new THREE.Vector3())
  const modelRadiusRef = useRef<number>(1)
  const requestRef = useRef<number>(0)
  const runtimeRef = useRef<{
    scene: THREE.Scene
    renderer: THREE.WebGLRenderer
    camera: THREE.PerspectiveCamera
    controls: OrbitControls
    model: THREE.Object3D | null
  } | null>(null)
  const showingModel = Boolean(modelUrl && !showRender && !error)

  useEffect(() => {
    if (!showingModel) {
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

    // Metals need a surrounding reflection environment, not just direct lights.
    // Generate the same studio lighting locally for every model.
    const room = new RoomEnvironment()
    const pmrem = new THREE.PMREMGenerator(renderer)
    const environment = pmrem.fromScene(room)
    scene.environment = environment.texture
    room.dispose()
    pmrem.dispose()

    const runtime = { scene, renderer, camera, controls, model: null as THREE.Object3D | null }
    runtimeRef.current = runtime

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
      runtimeRef.current = null
      if (runtime.model) disposeModel(runtime.model)
      cancelAnimationFrame(requestRef.current)
      resizeObserver.disconnect()
      controls.dispose()
      environment.dispose()
      renderer.dispose()
      scene.clear()
      if (container.contains(canvas)) {
        container.removeChild(canvas)
      }
    }
  }, [showingModel])

  useEffect(() => {
    const runtime = runtimeRef.current
    if (!modelUrl || !showingModel || !runtime) return
    const { scene, renderer, camera, controls } = runtime

    // Load Model
    const loader = new GLTFLoader()
    let disposed = false

    loader.load(
      modelUrl,
      (gltf) => {
        if (disposed) {
          disposeModel(gltf.scene)
          return
        }
        const model = gltf.scene

        // Some Blender exports retain anisotropy without tangents or UVs.
        // Fall back to ordinary metal shading instead of an undefined direction.
        model.traverse((object) => {
          if (!(object instanceof THREE.Mesh)) return
          const geometry = object.geometry
          if (geometry.hasAttribute("tangent") || geometry.hasAttribute("uv")) return
          const materials = Array.isArray(object.material) ? object.material : [object.material]
          for (const material of materials) {
            if (material instanceof THREE.MeshPhysicalMaterial && material.anisotropy > 0) {
              material.anisotropy = 0
              material.needsUpdate = true
            }
          }
        })

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
        const previousModel = runtime.model
        if (previousModel) scene.remove(previousModel)
        scene.add(model)
        runtime.model = model

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

        // Paint the replacement before publishing its loaded state.
        renderer.render(scene, camera)
        if (previousModel) disposeModel(previousModel)
        setLoadedUrl(modelUrl)
      },
      undefined,
      () => {
        if (!disposed) {
          setFailedUrl(modelUrl)
        }
      }
    )

    return () => { disposed = true }
  }, [modelUrl, showingModel])

  // Reset to original isometric camera view
  const resetCamera = useCallback(() => {
    const controls = controlsRef.current
    const camera = cameraRef.current
    if (!controls || !camera) return

    camera.position.copy(initialCamPos.current)
    controls.target.copy(initialTarget.current)
    controls.update()
  }, [])

  const content = (
    <>
      {/* 3D Model Viewport */}
      {modelUrl && !error && !showRender ? (
        <div className="relative w-full h-full">
          {loading && (
            <div className="model-loading" role="status">Loading model…</div>
          )}
          <div
            ref={containerRef}
            className="w-full h-full cursor-grab active:cursor-grabbing"
            aria-label={`Interactive 3D model: ${label}`}
          />

          {/* Floating Controls Overlay */}
          <div className="model-controls">
            <div className="model-axis-bar" role="toolbar" aria-label="Camera controls">
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
                  title="View render"
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
    </>
  )

  if (fillContainer) {
    return <div className="image-frame relative group w-full h-full">{content}</div>
  }

  return (
    <AspectRatio ratio={ratio} className="image-frame relative group">
      {content}
    </AspectRatio>
  )
}
