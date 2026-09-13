import { lazy, Suspense, useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { type Experiment } from "@/lib/experiments"

const Backdrop = lazy(() => import("@/components/backdrop"))

export function LandingPage({
  experiment,
  onBrowse,
}: {
  experiment?: Experiment
  onBrowse: () => void
}) {
  const [readyExperiment, setReadyExperiment] = useState<Experiment | null>(
    null
  )
  useEffect(() => {
    if (!experiment) return
    let cancelled = false
    const sources = [
      experiment.reference_preview ?? experiment.reference,
      ...experiment.runs.map((run) => run.render_preview ?? run.render),
    ]
    Promise.all(
      sources.map(async (src) => {
        if (!src) return
        const image = new Image()
        image.src = src
        await image.decode().catch(() => undefined)
      })
    ).then(() => {
      if (!cancelled) setReadyExperiment(experiment)
    })
    return () => {
      cancelled = true
    }
  }, [experiment])
  const previewsReady = Boolean(experiment && readyExperiment === experiment)
  const previews = experiment
    ? [
        {
          label: "Reference",
          src: experiment.reference_preview ?? experiment.reference,
        },
        ...experiment.runs.map((run) => ({
          label: run.name,
          src: run.render_preview ?? run.render,
        })),
      ]
    : ["Reference", "Codex", "Kimi Code", "Claude Code"].map((label) => ({
        label,
        src: null,
      }))

  return (
    <main className="landing-page">
      <section className="landing-intro">
        <Suspense fallback={null}>
          <Backdrop />
        </Suspense>
        <div className="landing-copy">
          <p className="landing-name">
            <img
              src={`${import.meta.env.BASE_URL}brand/meshmatch-mark.png`}
              width="32"
              height="32"
              alt=""
            />
            Meshmatch
          </p>
          <h1>
            How well can the same AI model reconstruct an object across
            different harnesses?
          </h1>
        </div>
      </section>
      <section className="landing-benchmark" aria-labelledby="benchmark-title">
        <h2 id="benchmark-title">Current benchmark</h2>
        <p className="landing-description">
          Meshmatch is a small, exploratory visual evaluation of how coding
          harnesses influence image-to-3D reconstruction. The current task set
          covers four objects: sunglasses, a mouse, a desk lamp, and a stapler.
        </p>
        <p className="landing-description">
          Across these tasks, I test Gemini 3.8 Flash High, GPT 5.6 Terra High,
          and GPT 5.6 Luna High in Codex, Claude Code, and Kimi Code. Results
          are presented side by side for direct visual inspection. The central
          question is whether pairing the same model and task with different
          coding harnesses produces meaningful visible differences.
        </p>
      </section>
      <section
        className="landing-methodology"
        aria-labelledby="methodology-title"
      >
        <h2 id="methodology-title">Methodology</h2>
        <p className="landing-description">
          I run the same AI model in Codex, Claude Code, and Kimi Code using
          each harness’s native <code>/goal</code> mode, which lets an agent
          work toward an objective through repeated tool use, inspection, and
          refinement. Each run receives the same reference image and prompt in
          an isolated Blender environment, with no downloaded assets. Each run
          has a 90-minute time limit. Runs that reach this limit are stopped,
          and their latest saved work is preserved as-is. Comparing the
          resulting reconstructions reveals how model–harness interaction shapes
          visual reasoning and the ability to turn it into 3D geometry.
        </p>
        <div className="project-links">
          <p>
            Find the source code on{" "}
            <a
              className="project-link"
              href="https://github.com/1shanra1/blender-bench-harness"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="View Meshmatch on GitHub (opens in a new tab)"
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="currentColor"
                aria-hidden="true"
              >
                <path d="M12 .297C5.37.297 0 5.67 0 12.297c0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.043-1.61-4.043-1.61-.546-1.387-1.333-1.756-1.333-1.756-1.09-.745.083-.729.083-.729 1.205.084 1.838 1.237 1.838 1.237 1.07 1.835 2.809 1.305 3.495.998.108-.776.418-1.305.762-1.605-2.665-.305-5.467-1.334-5.467-5.931 0-1.31.469-2.381 1.236-3.221-.124-.303-.536-1.524.117-3.176 0 0 1.008-.322 3.301 1.23a11.52 11.52 0 0 1 3.003-.404c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.655 1.652.243 2.873.12 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222 0 1.606-.015 2.898-.015 3.293 0 .322.216.694.825.576C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
              </svg>
              GitHub
            </a>
          </p>
          <p>
            Experiments ran on{" "}
            <a
              className="project-link"
              href="https://modal.com"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Modal (opens in a new tab)"
            >
              <img
                src={`${import.meta.env.BASE_URL}modal-logo.svg`}
                width="24"
                height="24"
                alt=""
              />
              Modal
            </a>
          </p>
        </div>
      </section>
      <div className="landing-preview-heading">
        <h2 id="featured-comparison-title">Featured comparison</h2>
        <p>Desk Lamp · Gemini 3.8 Flash High</p>
      </div>
      <section
        className={`landing-preview ${previewsReady ? "is-ready" : ""}`}
        aria-busy={!previewsReady}
        aria-labelledby="featured-comparison-title"
      >
        {previews.map((preview) => (
          <figure
            key={preview.label}
            style={{ visibility: previewsReady ? "visible" : "hidden" }}
          >
            <div>
              {preview.src && (
                <img src={preview.src} alt={`Desk Lamp — ${preview.label}`} />
              )}
            </div>
            <figcaption>{preview.label}</figcaption>
          </figure>
        ))}
      </section>
      <div className="landing-actions">
        <Button className="landing-cta" onClick={onBrowse}>
          View experiments
        </Button>
      </div>
    </main>
  )
}
