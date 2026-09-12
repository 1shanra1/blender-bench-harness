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
import { ModelInspectionModal } from "@/components/model-inspection-modal"
import { Button } from "@/components/ui/button"
import { AspectRatio } from "@/components/ui/aspect-ratio"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
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
  ratio = 1,
  className,
}: {
  src: string | null
  label: string
  onOpen: () => void
  ratio?: number
  className?: string
}) {
  const [failedSource, setFailedSource] = useState<string | null>(null)
  const [loaded, setLoaded] = useState(false)
  return (
    <AspectRatio ratio={ratio} className="image-frame">
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
            onLoad={() => setLoaded(true)}
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
            {src ? "Image unavailable" : "No final render"}
          </EmptyTitle>
        </Empty>
      )}
    </AspectRatio>
  )
}

function Comparison({
  experiment,
  modelTabs,
}: {
  experiment: Experiment
  modelTabs: ReactNode
}) {
  const [lightbox, setLightbox] = useState(-1)
  const [inspectingRunId, setInspectingRunId] = useState<string | null>(null)
  useEffect(() => {
    setLightbox(-1)
    setInspectingRunId(null)
  }, [experiment.id])
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
                src={images[0].src}
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
                  src={run.render}
                  label={`${modelName(run.model)} · ${run.name}`}
                  onOpen={() => openImage(run.render)}
                />
              </article>
            </div>
          ))}
        </div>
      </div>
      <Evolution key={experiment.id} runs={experiment.runs} />
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
        <ModelInspectionModal
          experiment={experiment}
          activeRunId={inspectingRunId}
          onClose={() => setInspectingRunId(null)}
          onSelectRun={(id) => setInspectingRunId(id)}
          onOpenRender={(src) => openImage(src)}
        />
      )}
    </>
  )
}

export default function App() {
  const [experiments, setExperiments] = useState<Experiment[] | null>(null)
  const [location, setLocation] = useState(() => ({
    view: new URLSearchParams(window.location.search).get("view"),
    experiment: new URLSearchParams(window.location.search).get("experiment"),
    model: new URLSearchParams(window.location.search).get("model") ?? "gemini",
  }))
  const navigationRequest = useRef(0)
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
          for (const run of item.runs) {
            run.render = assetUrl(run.render)
            run.evolution = run.evolution?.map((frame) => ({ ...frame, src: assetUrl(frame.src)! }))
            run.model_url = assetUrl(run.model_url)
            for (const [axis] of axes)
              run.views[axis] = assetUrl(run.views[axis])
          }
          const harnessOrder = ["codex", "kimi", "claude"]
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
        view: params.get("view"),
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
        variants: {},
      }
      const key = modelKey(batch.runs[0]?.model ?? batch.id)
      current.reference ??= batch.reference
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
    model = selectedModel,
    view = "experiments"
  ) => {
    const request = ++navigationRequest.current
    const target = groups.find((item) => item.id === experimentId)
    const batch =
      target?.variants[model] ?? Object.values(target?.variants ?? {})[0]
    if (batch) {
      // Keep the current comparison visible until the next images are decoded.
      const sources = [batch.reference, ...batch.runs.map((run) => run.render)]
      await Promise.all(
        sources.filter(Boolean).map(async (src) => {
          const image = new Image()
          image.src = src!
          await image.decode().catch(() => undefined)
        })
      )
    }
    if (request !== navigationRequest.current) return

    const url = new URL(window.location.href)
    url.searchParams.delete("view")
    if (experimentId) {
      url.searchParams.set("experiment", experimentId)
      url.searchParams.set("model", model)
    } else {
      url.searchParams.delete("experiment")
      url.searchParams.delete("model")
      if (view === "experiments") url.searchParams.set("view", "experiments")
    }
    window.history.pushState({}, "", url)
    setLocation({ experiment: experimentId, model, view })
  }
  const modelTabs = group ? (
    <div className="model-tabs" role="tablist" aria-label="Choose model">
      {["gemini", "luna"]
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
  if (!location.experiment && location.view !== "experiments") {
    const featured = groups.find((item) => item.id === "desk-lamp")?.variants
      .gemini
    return <LandingPage experiment={featured} onBrowse={() => navigate(null)} />
  }
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to results
      </a>
      <main id="main" className="workspace">
        <div
          className={`page-heading ${group ? "detail-heading" : "gallery-heading"}`}
        >
          <Suspense fallback={null}>
            <Backdrop />
          </Suspense>
          <div className="heading-content">
            <div className="title-row">
              <div className="experiment-title">
                <button
                  className="back-to-experiments"
                  type="button"
                  aria-label={group ? "Back to experiments" : "Back to home"}
                  title={group ? "Back to experiments" : "Back to home"}
                  onClick={() =>
                    navigate(
                      null,
                      selectedModel,
                      group ? "experiments" : "home"
                    )
                  }
                >
                  <ArrowLeft size={20} aria-hidden="true" />
                </button>
                <h1>
                  {group ? (
                    <Select
                      value={group.id}
                      onValueChange={(value) =>
                        value && navigate(value, selectedModel)
                      }
                      items={groups.map((item) => ({
                        value: item.id,
                        label: item.name,
                      }))}
                    >
                      <SelectTrigger
                        aria-label="Choose experiment"
                        className="experiment-title-select"
                      >
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent
                        alignItemWithTrigger={false}
                        align="start"
                        className="experiment-menu"
                      >
                        <SelectGroup>
                          <SelectLabel>Choose experiment</SelectLabel>
                          {groups.map((item) => (
                            <SelectItem key={item.id} value={item.id}>
                              {item.name}
                            </SelectItem>
                          ))}
                        </SelectGroup>
                      </SelectContent>
                    </Select>
                  ) : (
                    "Experiments"
                  )}
                </h1>
              </div>
            </div>
          </div>
        </div>
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
          <Comparison experiment={experiment} modelTabs={modelTabs} />
        ) : groups.length > 0 ? (
          <div className="experiment-gallery" aria-label="Experiments">
            {groups.map((item) => (
              <button
                key={item.id}
                type="button"
                className="experiment-card"
                onClick={() => navigate(item.id, location.model)}
              >
                <div className="experiment-card-image">
                  {item.reference ? (
                    <img src={item.reference} alt={`${item.name} reference`} />
                  ) : (
                    <ImageOff size={28} />
                  )}
                </div>
                <h2>{item.name}</h2>
              </button>
            ))}
          </div>
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
