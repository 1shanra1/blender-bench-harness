import { lazy, Suspense } from "react"
import { ArrowRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { type Experiment } from "@/lib/experiments"

const Backdrop = lazy(() => import("@/components/backdrop"))

export function LandingPage({ experiment, onBrowse }: {
  experiment?: Experiment
  onBrowse: () => void
}) {
  const previews = experiment ? [
    { label: "Reference", src: experiment.reference },
    ...experiment.runs.map((run) => ({ label: run.name, src: run.render })),
  ] : []

  return (
    <main className="landing-page">
      <section className="landing-intro">
        <Suspense fallback={null}><Backdrop /></Suspense>
        <div className="landing-copy">
          <p className="landing-name">Blender Bench</p>
          <h1>How well can the same AI model reconstruct an object across different harnesses?</h1>
          <p className="landing-description">
            Given a reference image and each harness’s native goal mode, models
            build, inspect, and refine a 3D reconstruction in Blender. We examine
            model–harness interaction, visual reasoning, and the ability to
            translate that reasoning into 3D geometry.
          </p>
          <Button className="landing-cta" onClick={onBrowse}>
            View experiments <ArrowRight size={16} aria-hidden="true" />
          </Button>
        </div>
      </section>
      {previews.length > 0 && (
        <section className="landing-preview" aria-label="Desk Lamp reconstructed with Gemini 3.8 Flash High">
          {previews.map((preview) => (
            <figure key={preview.label}>
              <div>{preview.src && <img src={preview.src} alt={`Desk Lamp — ${preview.label}`} />}</div>
              <figcaption>{preview.label}</figcaption>
            </figure>
          ))}
        </section>
      )}
    </main>
  )
}
