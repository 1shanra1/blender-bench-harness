import {
  lazy,
  Suspense,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react"
import {
  ArrowLeft,
  Box,
  CircleAlert,
  ImageOff,
  Maximize2,
  RotateCw,
} from "lucide-react"
import Lightbox from "yet-another-react-lightbox"
import Captions from "yet-another-react-lightbox/plugins/captions"
import Zoom from "yet-another-react-lightbox/plugins/zoom"
import { LandingPage } from "@/components/landing-page"
import { Metrics } from "@/components/metrics"
import { Evolution } from "@/components/evolution"
const ModelInspectionModal = lazy(() =>
  import("@/components/model-inspection-modal").then((module) => ({
    default: module.ModelInspectionModal,
  }))
)
import { Button } from "@/components/ui/button"
import { AspectRatio } from "@/components/ui/aspect-ratio"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import {
  axes,
  modelKey,
  modelName,
  type Experiment,
  type ExperimentGroup,
} from "@/lib/experiments"

const Backdrop = lazy(() => import("@/components/backdrop"))

function ImageFrame({
  src,
  label,
  onOpen,
  ratio,
  className,
  emptyLabel = "No final render",
}: {
  src: string | null
  label: string
  onOpen: () => void
  ratio?: number
  className?: string
  emptyLabel?: string
}) {
  const [failedSource, setFailedSource] = useState<string | null>(null)
  const [loaded, setLoaded] = useState(() => Boolean(ratio))
  const [naturalRatio, setNaturalRatio] = useState<number | null>(null)
  return (
    <AspectRatio ratio={ratio ?? naturalRatio ?? 1} className="image-frame">
      {src && failedSource !== src ? (
        <button
          className="image-button"
          onClick={onOpen}
          aria-label={`Enlarge ${label}`}
        >
          {!loaded && <Skeleton className="absolute inset-0 rounded-none" />}
          <img
            src={src}
            alt={label}
            className={className}
            onLoad={(event) => {
              const image = event.currentTarget
              setNaturalRatio(image.naturalWidth / image.naturalHeight)
              setLoaded(true)
            }}
            onError={() => setFailedSource(src)}
          />
          <span className="enlarge-icon" aria-hidden="true">
            <Maximize2 size={15} />
          </span>
        </button>
      ) : (
        <Empty className="absolute inset-0 gap-2 p-4">
          <EmptyMedia>
            <ImageOff size={24} strokeWidth={1.3} />
          </EmptyMedia>
          <EmptyTitle className="font-normal text-muted-foreground">
            {src ? "Image unavailable" : emptyLabel}
          </EmptyTitle>
        </Empty>
      )}
    </AspectRatio>
  )
}

function Comparison({
  experiment,
  modelTabs,
  imageRatios,
}: {
  experiment: Experiment
  modelTabs: ReactNode
  imageRatios: ReadonlyMap<string, number>
}) {
  const [lightbox, setLightbox] = useState(-1)
  const [inspectingRunId, setInspectingRunId] = useState<string | null>(null)
  const firstModel = experiment.runs.find((run) => run.model_url)
  const images = [
    { src: experiment.reference, alt: `${experiment.name} — reference image` },
    ...experiment.runs.map((run) => ({
      src: run.render,
      alt: `${experiment.name} — ${modelName(run.model)} · ${run.name}`,
    })),
  ]
  const slides = images.filter(
    (item): item is { src: string; alt: string } => item.src !== null
  )
  const openImage = (src: string | null) =>
    setLightbox(slides.findIndex((item) => item.src === src))
  const previewRatio = (src: string | null) =>
    src ? imageRatios.get(src) : undefined
  return (
    <>
      <div className="comparison-toolbar">
        {modelTabs}
        {firstModel && (
          <Button
            variant="outline"
            className="inspect-models"
            onClick={() => setInspectingRunId(firstModel.id)}
          >
            <Box size={16} aria-hidden="true" /> Inspect in 3D
          </Button>
        )}
      </div>
      <div className="comparison">
        <div className="comparison-grid">
          <div className="comparison-column">
            <article className="render-card">
              <header className="render-header reference-header">
                <h2>Reference</h2>
              </header>
              <ImageFrame
                src={experiment.reference_preview ?? images[0].src}
                ratio={previewRatio(
                  experiment.reference_preview ?? images[0].src
                )}
                label={images[0].alt}
                className="reference-img"
                onOpen={() => openImage(images[0].src)}
              />
            </article>
          </div>
          {experiment.runs.map((run) => (
            <div key={run.id} className="comparison-column">
              <article className="render-card">
                <header className="render-header">
                  <h2>{run.name}</h2>
                </header>
                <ImageFrame
                  key={run.id}
                  src={run.render_preview ?? run.render}
                  ratio={previewRatio(run.render_preview ?? run.render)}
                  emptyLabel={
                    run.status.endsWith("failed")
                      ? "Awaiting rerun"
                      : "No final render"
                  }
                  label={`${modelName(run.model)} · ${run.name}`}
                  onOpen={() => openImage(run.render)}
                />
              </article>
            </div>
          ))}
        </div>
      </div>
      <Evolution
        key={experiment.id}
        runs={experiment.runs}
        imageRatios={imageRatios}
      />
      <Metrics runs={experiment.runs} />
      <Lightbox
        open={lightbox >= 0}
        close={() => setLightbox(-1)}
        index={Math.max(0, lightbox)}
        slides={slides.map((slide) => ({ ...slide, title: slide.alt }))}
        plugins={[Zoom, Captions]}
        carousel={{ finite: true }}
        controller={{ closeOnBackdropClick: true }}
        animation={{ fade: 150, swipe: 200 }}
      />
      {inspectingRunId && (
        <Suspense fallback={null}>
          <ModelInspectionModal
            experiment={experiment}
            activeRunId={inspectingRunId}
            onClose={() => setInspectingRunId(null)}
            onSelectRun={(id) => setInspectingRunId(id)}
            onOpenRender={(src) => openImage(src)}
          />
        </Suspense>
      )}
    </>
  )
}

export default function App() {
  const [experiments, setExperiments] = useState<Experiment[] | null>(null)
  const [location, setLocation] = useState(() => ({
    experiment: new URLSearchParams(window.location.search).get("experiment"),
    model: new URLSearchParams(window.location.search).get("model") ?? "gemini",
  }))
  const navigationRequest = useRef(0)
  const [imageRatios, setImageRatios] = useState(
    () => new Map<string, number>()
  )
  const [error, setError] = useState(false)
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    const dataUrl = new URL(
      `${import.meta.env.BASE_URL}data/results.json`,
      window.location.href
    )
    fetch(dataUrl, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("Could not load results")
        return response.json()
      })
      .then((data) => {
        if (!Array.isArray(data.experiments)) throw new Error("Invalid results")
        // Bundle paths are relative to results.json, including on subpath deployments.
        const assetUrl = (path: string | null) =>
          path ? new URL(path, dataUrl).href : null
        for (const item of data.experiments as Experiment[]) {
          item.reference = assetUrl(item.reference)
          item.reference_preview = assetUrl(item.reference_preview ?? null)
          for (const run of item.runs) {
            run.render = assetUrl(run.render)
            run.render_preview = assetUrl(run.render_preview ?? null)
            run.evolution = run.evolution?.map((frame) => ({
              ...frame,
              src: assetUrl(frame.src)!,
            }))
            run.model_url = assetUrl(run.model_url)
            for (const [axis] of axes)
              run.views[axis] = assetUrl(run.views[axis])
          }
          const harnessOrder = ["codex", "claude", "kimi"]
          const harnessRank = (id: string) => {
            const rank = harnessOrder.indexOf(id)
            return rank < 0 ? harnessOrder.length : rank
          }
          item.runs.sort((a, b) => harnessRank(a.id) - harnessRank(b.id))
        }
        setExperiments(data.experiments)
      })
      .catch(() => {
        if (!controller.signal.aborted) setError(true)
      })
    return () => controller.abort()
  }, [attempt])

  useEffect(() => {
    const onPopState = () => {
      navigationRequest.current += 1
      const params = new URLSearchParams(window.location.search)
      setLocation({
        experiment: params.get("experiment"),
        model: params.get("model") ?? "gemini",
      })
    }
    window.addEventListener("popstate", onPopState)
    return () => window.removeEventListener("popstate", onPopState)
  }, [])

  const groups = useMemo<ExperimentGroup[]>(() => {
    if (!experiments) return []
    const grouped = new Map<string, ExperimentGroup>()
    for (const batch of experiments) {
      if (batch.name.trim().toLowerCase() === "kettle") continue
      const id = batch.name
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/(^-|-$)/g, "")
      const current = grouped.get(id) ?? {
        id,
        name: batch.name,
        reference: batch.reference,
        reference_preview: batch.reference_preview,
        variants: {},
      }
      const key = modelKey(batch.runs[0]?.model ?? batch.id)
      current.reference ??= batch.reference
      current.reference_preview ??= batch.reference_preview
      current.variants[key] = batch
      grouped.set(id, current)
    }
    return [...grouped.values()]
  }, [experiments])

  const group = groups.find((item) => item.id === location.experiment)
  const availableModels = group ? Object.keys(group.variants) : []
  const selectedModel = availableModels.includes(location.model)
    ? location.model
    : (availableModels[0] ?? location.model)
  const experiment = group?.variants[selectedModel]

  const navigate = async (
    experimentId: string | null,
    model = selectedModel
  ) => {
    const request = ++navigationRequest.current
    const target = groups.find((item) => item.id === experimentId)
    const batch =
      target?.variants[model] ?? Object.values(target?.variants ?? {})[0]
    const decodedRatios = new Map<string, number>()
    if (batch) {
      // Keep the current comparison visible until the next images are decoded.
      const sources = [
        batch.reference_preview ?? batch.reference,
        ...batch.runs.map((run) => run.render_preview ?? run.render),
        ...batch.runs.map((run) => run.evolution?.[0]?.src ?? null),
      ]
      await Promise.all(
        sources.filter(Boolean).map(async (src) => {
          const image = new Image()
          image.src = src!
          await image.decode().catch(() => undefined)
          if (image.naturalWidth && image.naturalHeight) {
            decodedRatios.set(src!, image.naturalWidth / image.naturalHeight)
          }
        })
      )
    }
    if (request !== navigationRequest.current) return
    if (decodedRatios.size) {
      setImageRatios((current) => {
        const next = new Map(current)
        decodedRatios.forEach((ratio, src) => next.set(src, ratio))
        return next
      })
    }

    const url = new URL(window.location.href)
    url.searchParams.delete("view")
    if (experimentId) {
      url.searchParams.set("experiment", experimentId)
      url.searchParams.set("model", model)
    } else {
      url.searchParams.delete("experiment")
      url.searchParams.delete("model")
    }
    window.history.pushState({}, "", url)
    setLocation({ experiment: experimentId, model })
    window.scrollTo(0, 0)
  }
  const modelTabs = group ? (
    <div className="model-tabs" role="tablist" aria-label="Choose model">
      {["gemini", "luna", "terra"]
        .filter((key) => group.variants[key])
        .map((key) => {
          const batch = group.variants[key]
          return (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={key === selectedModel}
              className={key === selectedModel ? "active" : ""}
              onClick={() => navigate(group.id, key)}
            >
              {modelName(batch.runs[0]?.model ?? key)}
            </button>
          )
        })}
    </div>
  ) : null
  const objectTabs = group ? (
    <nav className="experiment-tabs" aria-label="Choose object">
      <div className="experiment-tabs-list" role="tablist">
        {groups.map((item) => {
          const isSelected = item.id === group.id
          const nextModel = item.variants[selectedModel]
            ? selectedModel
            : item.variants.gemini
              ? "gemini"
              : Object.keys(item.variants)[0]
          return (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={isSelected}
              className={isSelected ? "active" : ""}
              onClick={() => navigate(item.id, nextModel)}
            >
              {item.name}
            </button>
          )
        })}
      </div>
    </nav>
  ) : null
  if (!location.experiment) {
    const featured = groups.find((item) => item.id === "desk-lamp")?.variants
      .gemini
    const firstExperiment =
      groups.find((item) => item.id === "sunglasses") ?? groups[0]
    const firstModel = firstExperiment?.variants.gemini
      ? "gemini"
      : Object.keys(firstExperiment?.variants ?? {})[0]
    return (
      <LandingPage
        experiment={featured}
        onBrowse={() => {
          if (firstExperiment && firstModel) {
            navigate(firstExperiment.id, firstModel)
          }
        }}
      />
    )
  }
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to results
      </a>
      <main id="main" className="workspace">
        <div className="page-heading detail-heading">
          <Suspense fallback={null}>
            <Backdrop />
          </Suspense>
          <div className="heading-content">
            <div className="title-row">
              <div className="experiment-title">
                <button
                  className="back-to-experiments"
                  type="button"
                  aria-label="Back to home"
                  title="Back to home"
                  onClick={() => navigate(null, selectedModel)}
                >
                  <ArrowLeft size={20} aria-hidden="true" />
                </button>
                <h1>{group?.name ?? "Experiment"}</h1>
              </div>
            </div>
          </div>
        </div>
        {objectTabs}
        {error ? (
          <Empty className="page-empty">
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <CircleAlert />
              </EmptyMedia>
              <EmptyTitle>Couldn’t load your runs</EmptyTitle>
              <EmptyDescription>
                The published results could not be loaded. Please try again.
              </EmptyDescription>
            </EmptyHeader>
            <Button
              variant="outline"
              onClick={() => {
                setError(false)
                setAttempt((value) => value + 1)
              }}
            >
              <RotateCw />
              Retry
            </Button>
          </Empty>
        ) : experiments === null ? (
          <div
            className="comparison-grid loading-grid"
            aria-label="Loading experiments"
            role="status"
          >
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-80 rounded-lg" />
            ))}
          </div>
        ) : experiment ? (
          <Comparison
            key={experiment.id}
            experiment={experiment}
            modelTabs={modelTabs}
            imageRatios={imageRatios}
          />
        ) : (
          <Empty className="page-empty">
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <Box />
              </EmptyMedia>
              <EmptyTitle>No saved experiments</EmptyTitle>
              <EmptyDescription>
                Published experiments will appear here.
              </EmptyDescription>
            </EmptyHeader>
          </Empty>
        )}
      </main>
    </div>
  )
}
