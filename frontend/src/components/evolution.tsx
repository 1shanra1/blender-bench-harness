import { useEffect, useRef, useState } from "react"
import { Pause, Play } from "lucide-react"
import { duration, type Run } from "@/lib/experiments"

type Sequence = {
  id: string
  name: string
  frames: NonNullable<Run["evolution"]>
}

export function Evolution({ runs }: { runs: Run[] }) {
  const section = useRef<HTMLElement>(null)
  const [sequences, setSequences] = useState<Sequence[] | null>(null)
  const [playing, setPlaying] = useState(
    () => !window.matchMedia("(prefers-reduced-motion: reduce)").matches
  )
  const [visible, setVisible] = useState(false)
  const [step, setStep] = useState(0)
  const available = runs.some((run) => (run.evolution?.length ?? 0) > 1)

  useEffect(() => {
    if (!available) return
    let cancelled = false
    Promise.all(
      runs.map(async (run) => {
        const frames = await Promise.all(
          (run.evolution ?? []).map(async (frame) => {
            const image = new Image()
            image.src = frame.src
            try {
              await image.decode()
              return frame
            } catch {
              return null
            }
          })
        )
        return {
          id: run.id,
          name: run.name,
          frames: frames.filter((frame) => frame !== null),
        }
      })
    ).then((loaded) => {
      if (!cancelled) setSequences(loaded)
    })
    return () => {
      cancelled = true
    }
  }, [runs, available])

  useEffect(() => {
    if (!section.current) return
    const observer = new IntersectionObserver(([entry]) =>
      setVisible(entry.isIntersecting)
    )
    observer.observe(section.current)
    return () => observer.disconnect()
  }, [available])

  useEffect(() => {
    if (!playing || !visible || !sequences) return
    const timer = window.setInterval(() => {
      if (!document.hidden) setStep((current) => current + 1)
    }, 1800)
    return () => window.clearInterval(timer)
  }, [playing, visible, sequences])

  if (!available) return null
  const ordered = ["codex", "claude", "kimi"]
  const cards = (
    sequences ?? runs.map((run) => ({ id: run.id, name: run.name, frames: [] }))
  )
    .slice()
    .sort((a, b) => ordered.indexOf(a.id) - ordered.indexOf(b.id))

  return (
    <section
      className="evolution"
      ref={section}
      aria-labelledby="evolution-title"
    >
      <header className="evolution-heading">
        <h2 id="evolution-title">Evolution</h2>
        <button
          className="evolution-play"
          type="button"
          onClick={() => setPlaying((value) => !value)}
          aria-label={
            playing ? "Pause render sequences" : "Play render sequences"
          }
        >
          {playing ? (
            <Pause size={14} aria-hidden="true" />
          ) : (
            <Play size={14} aria-hidden="true" />
          )}
          {playing ? "Pause" : "Play"}
        </button>
      </header>
      <div className="evolution-grid">
        {cards.map((sequence) => {
          // Hold the final checkpoint for one extra beat before looping.
          const index = Math.min(
            step % (sequence.frames.length + 1),
            sequence.frames.length - 1
          )
          const frame = sequence.frames[index]
          return (
            <article className="evolution-card" key={sequence.id}>
              <h3>{sequence.name}</h3>
              <div className="evolution-image">
                {frame ? (
                  <>
                    <img
                      src={frame.src}
                      alt={`${sequence.name} — ${frame.final ? "final render" : `saved render at ${duration(frame.elapsed_seconds)}`}`}
                    />
                    <span className="evolution-time">
                      {frame.final ? "Final" : ""}
                      {frame.final && frame.elapsed_seconds !== null
                        ? " · "
                        : ""}
                      {frame.elapsed_seconds !== null
                        ? duration(frame.elapsed_seconds)
                        : ""}
                    </span>
                  </>
                ) : (
                  <span className="evolution-empty">
                    {sequences ? "No saved sequence" : "Loading sequence…"}
                  </span>
                )}
              </div>
            </article>
          )
        })}
      </div>
    </section>
  )
}
