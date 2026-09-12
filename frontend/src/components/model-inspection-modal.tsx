import { useEffect } from "react"
import { X } from "lucide-react"
import { ModelViewer } from "@/components/model-viewer"
import { modelName, type Experiment } from "@/lib/experiments"

interface ModelInspectionModalProps {
  experiment: Experiment
  activeRunId: string
  onClose: () => void
  onSelectRun: (runId: string) => void
  onOpenRender?: (src: string | null) => void
}

export function ModelInspectionModal({
  experiment,
  activeRunId,
  onClose,
  onSelectRun,
  onOpenRender,
}: ModelInspectionModalProps) {
  const activeRun =
    experiment.runs.find((run) => run.id === activeRunId) ?? experiment.runs[0]

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault()
        onClose()
      } else if (e.key === "ArrowLeft") {
        e.preventDefault()
        const index = experiment.runs.findIndex((r) => r.id === activeRunId)
        if (index > 0) {
          onSelectRun(experiment.runs[index - 1].id)
        } else if (index === 0 && experiment.runs.length > 1) {
          onSelectRun(experiment.runs[experiment.runs.length - 1].id)
        }
      } else if (e.key === "ArrowRight") {
        e.preventDefault()
        const index = experiment.runs.findIndex((r) => r.id === activeRunId)
        if (index >= 0 && index < experiment.runs.length - 1) {
          onSelectRun(experiment.runs[index + 1].id)
        } else if (
          index === experiment.runs.length - 1 &&
          experiment.runs.length > 1
        ) {
          onSelectRun(experiment.runs[0].id)
        }
      }
    }

    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [experiment.runs, activeRunId, onClose, onSelectRun])

  useEffect(() => {
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = "hidden"
    return () => {
      document.body.style.overflow = prevOverflow
    }
  }, [])

  if (!activeRun) return null

  return (
    <div
      className="inspection-overlay"
      role="dialog"
      aria-modal="true"
      aria-label={`Inspecting 3D model: ${activeRun.name}`}
    >
      <header className="inspection-header">
        <div className="inspection-header-info">
          <div>
            <h2>{modelName(activeRun.model)}</h2>
            <p>{activeRun.name}</p>
          </div>
        </div>

        <div
          className="inspection-switcher"
          role="tablist"
          aria-label="Switch harness"
        >
          {experiment.runs.map((run) => {
            const isSelected = run.id === activeRun.id
            return (
              <button
                key={run.id}
                type="button"
                role="tab"
                aria-selected={isSelected}
                className={`inspection-tab ${isSelected ? "active" : ""}`}
                onClick={() => onSelectRun(run.id)}
              >
                <span>{run.name}</span>
              </button>
            )
          })}
        </div>

        <div className="inspection-header-actions">
          <button
            type="button"
            className="inspection-close-btn"
            onClick={onClose}
            aria-label="Close overlay"
            title="Close (Esc)"
          >
            <X size={15} />
          </button>
        </div>
      </header>

      <div className="inspection-body">
        {experiment.reference && (
          <div className="inspection-floating-reference">
            <div className="inspection-floating-reference-header">
              Reference
            </div>
            <img
              src={experiment.reference}
              alt={`${experiment.name} reference`}
              onClick={() => onOpenRender?.(experiment.reference)}
              title="Click to enlarge reference"
            />
          </div>
        )}

        <div className="inspection-viewport-wrap">
          <ModelViewer
            key={activeRun.id}
            modelUrl={activeRun.model_url}
            renderUrl={activeRun.render}
            label={`${modelName(activeRun.model)} · ${activeRun.name}`}
            fillContainer
            onOpenRender={() => onOpenRender?.(activeRun.render)}
          />
        </div>
      </div>
    </div>
  )
}
