import { lazy, Suspense, useEffect, useState } from "react"
import {
  Box,
  Check,
  CircleAlert,
  ImageOff,
  Maximize2,
  RotateCw,
} from "lucide-react"
import Lightbox from "yet-another-react-lightbox"
import Captions from "yet-another-react-lightbox/plugins/captions"
import { Metrics } from "@/components/metrics"
import Zoom from "yet-another-react-lightbox/plugins/zoom"
import { Button } from "@/components/ui/button"
import { AspectRatio } from "@/components/ui/aspect-ratio"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
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
  duration,
  modelName,
  pairColors,
  pairLetters,
  runStatus,
  type Axis,
  type Experiment,
} from "@/lib/experiments"

const Backdrop = lazy(() => import("@/components/backdrop"))

function ImageFrame({
  src,
  label,
  onOpen,
}: {
  src: string | null
  label: string
  onOpen: () => void
}) {
  const [failed, setFailed] = useState(false)
  const [loaded, setLoaded] = useState(false)
  return (
    <AspectRatio ratio={1.42} className="image-frame">
      {src && !failed ? (
        <button
          className="image-button"
          onClick={onOpen}
          aria-label={`Enlarge ${label}`}
        >
          {!loaded && <Skeleton className="absolute inset-0 rounded-none" />}
          <img
            src={src}
            alt={label}
            onLoad={() => setLoaded(true)}
            onError={() => setFailed(true)}
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
            {failed ? "Image unavailable" : "No final render"}
          </EmptyTitle>
        </Empty>
      )}
    </AspectRatio>
  )
}

function Comparison({ experiment }: { experiment: Experiment }) {
  const [mode, setMode] = useState("agent")
  const [axis, setAxis] = useState<Axis>("positive_y")
  const [lightbox, setLightbox] = useState(-1)
  const images = [
    { src: experiment.reference, alt: `${experiment.name} — reference image` },
    ...experiment.runs.map((run) => ({
      src: mode === "agent" ? run.render : run.views[axis],
      alt: `${experiment.name} — ${modelName(run.model)} · ${run.name}${mode === "views" ? ` · ${axes.find(([key]) => key === axis)?.[1]}` : ""}`,
    })),
  ]
  const slides = images.filter(
    (item): item is { src: string; alt: string } => item.src !== null
  )
  const openImage = (src: string | null) =>
    setLightbox(slides.findIndex((item) => item.src === src))
  return (
    <>
      <Tabs
        value={mode}
        onValueChange={(value) => {
          setMode(String(value))
          setLightbox(-1)
        }}
        className="comparison"
      >
        <div className="comparison-toolbar">
          <TabsList aria-label="Render source">
            <TabsTrigger value="agent" className="px-3">
              Agent render
            </TabsTrigger>
            <TabsTrigger value="views" className="px-3">
              Independent views
            </TabsTrigger>
          </TabsList>
          {mode === "views" && (
            <Select
              value={axis}
              onValueChange={(value) => {
                if (value) setAxis(value as Axis)
              }}
              items={axes.map(([value, label]) => ({ value, label }))}
            >
              <SelectTrigger aria-label="Camera axis" className="axis-select">
                <Box size={14} />
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {axes.map(([value, label]) => (
                  <SelectItem key={value} value={value}>
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>
        <TabsContent value={mode} className="comparison-grid">
          <div className="comparison-column">
            <article className="render-card">
              <header className="render-header reference-header">
                <h2>Reference image</h2>
              </header>
              <ImageFrame
                key={images[0].src}
                src={images[0].src}
                label={images[0].alt}
                onOpen={() => openImage(images[0].src)}
              />
            </article>
          </div>
          {experiment.runs.map((run, i) => (
            <div key={run.id} className="comparison-column">
              <article className="render-card">
                <header className="render-header">
                  <span
                    className="pair-badge"
                    style={{ color: pairColors[run.id] }}
                  >
                    {pairLetters[run.id]}
                  </span>
                  <div>
                    <h2>{modelName(run.model)}</h2>
                    <p>
                      {run.name}
                      {run.effort
                        ? ` · ${run.effort.charAt(0).toUpperCase() + run.effort.slice(1)}`
                        : ""}
                    </p>
                  </div>
                </header>
                <ImageFrame
                  key={images[i + 1].src ?? `${run.id}-${mode}-${axis}`}
                  src={images[i + 1].src}
                  label={images[i + 1].alt}
                  onOpen={() => openImage(images[i + 1].src)}
                />
              </article>
              <div className="render-meta">
                <span
                  className={
                    run.native_complete === true ? "status-complete" : ""
                  }
                >
                  {run.native_complete === true ? (
                    <Check size={12} />
                  ) : (
                    <CircleAlert size={12} />
                  )}
                  {runStatus(run)}
                </span>
                <span>{duration(run.elapsed_seconds)}</span>
              </div>
            </div>
          ))}
        </TabsContent>
      </Tabs>
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
    </>
  )
}

export default function App() {
  const [experiments, setExperiments] = useState<Experiment[] | null>(null)
  const [selected, setSelected] = useState("")
  const [error, setError] = useState(false)
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    fetch("/api/experiments", { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("Could not load results")
        return response.json()
      })
      .then((data) => {
        if (!Array.isArray(data.experiments)) throw new Error("Invalid results")
        setExperiments(data.experiments)
        setSelected((previous) =>
          data.experiments.some((item: Experiment) => item.id === previous)
            ? previous
            : ((
                data.experiments.find(
                  (item: Experiment) =>
                    item.runs.length === 3 &&
                    item.runs.every((run) => run.render)
                ) ?? data.experiments[0]
              )?.id ?? "")
        )
      })
      .catch(() => {
        if (!controller.signal.aborted) setError(true)
      })
    return () => controller.abort()
  }, [attempt])
  const experiment = experiments?.find((item) => item.id === selected)
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to results
      </a>
      <header className="site-header">
        <div className="brand">
          <span className="brand-icon">
            <Box size={20} strokeWidth={1.4} />
          </span>
          Blender Bench
          <span className="brand-divider" />
          <span className="brand-section">Experiments</span>
        </div>
      </header>
      <main id="main" className="workspace">
        <div className="page-heading">
          <Suspense fallback={null}>
            <Backdrop />
          </Suspense>
          <div className="heading-content">
            <h1>{experiment?.name ?? "Experiments"}</h1>
          </div>
          {experiments && experiments.length > 0 && (
            <Select
              value={selected}
              onValueChange={(value) => {
                if (value) setSelected(value)
              }}
              items={experiments.map((item) => ({
                value: item.id,
                label: item.name,
              }))}
            >
              <SelectTrigger
                aria-label="Choose experiment"
                className="experiment-select"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent align="end" className="min-w-64">
                {experiments.map((item) => (
                  <SelectItem key={item.id} value={item.id}>
                    <span className="flex flex-col gap-1 py-1">
                      <span>{item.name}</span>
                      <span className="text-[10px] text-muted-foreground">
                        {item.id.slice(0, 4)}-{item.id.slice(4, 6)}-
                        {item.id.slice(6, 8)} · {item.id.slice(-8)}
                      </span>
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>
        {error ? (
          <Empty className="page-empty">
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <CircleAlert />
              </EmptyMedia>
              <EmptyTitle>Couldn’t load your runs</EmptyTitle>
              <EmptyDescription>
                Check that the local results server is running.
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
          <Comparison key={experiment.id} experiment={experiment} />
        ) : (
          <Empty className="page-empty">
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <Box />
              </EmptyMedia>
              <EmptyTitle>No saved experiments</EmptyTitle>
              <EmptyDescription>
                Collected runs in outputs/experiments will appear here.
              </EmptyDescription>
            </EmptyHeader>
          </Empty>
        )}
      </main>
    </div>
  )
}
