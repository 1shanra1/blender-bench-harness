import { type ReactNode } from "react"
import { Info } from "lucide-react"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { duration, pairColors, type Run } from "@/lib/experiments"

const count = new Intl.NumberFormat("en-US", {
  notation: "compact",
  maximumFractionDigits: 2,
})
const exact = new Intl.NumberFormat("en-US")

function MetricPanel({
  title,
  unit,
  detail,
  children,
  footer,
}: {
  title: string
  unit?: string
  detail?: string
  children: ReactNode
  footer: string
}) {
  return (
    <section className="metric-card" aria-label={title}>
      <header className="metric-heading">
        <h2>{title}</h2>
        <div>
          {unit && <span>{unit}</span>}
          {detail && (
            <Tooltip>
              <TooltipTrigger
                aria-label={`About ${title.toLowerCase()}`}
                className="info-trigger"
              >
                <Info size={13} />
              </TooltipTrigger>
              <TooltipContent className="leading-relaxed">
                {detail}
              </TooltipContent>
            </Tooltip>
          )}
        </div>
      </header>
      <div className="metric-body">{children}</div>
      <p className="metric-footer">{footer}</p>
    </section>
  )
}

export function Metrics({ runs }: { runs: Run[] }) {
  const maxSeconds = Math.max(
    ...runs.map((run) => run.elapsed_seconds ?? 0),
    1
  )
  const maxTokens = Math.max(
    ...runs.map((run) => run.usage?.tokens ?? 0),
    1
  )

  const missingTime = runs
    .filter((run) => run.elapsed_seconds === null)
    .map((run) => run.name)

  return (
    <div className="metrics-grid">
      <MetricPanel
        title="Wall clock"
        unit="Minutes"
        footer={
          missingTime.length
            ? `No elapsed time recorded for ${missingTime.join(", ")}.`
            : "Elapsed time per run"
        }
      >
        <div className="dither-bar-list" role="list">
          {runs.map((run) => {
            const seconds = run.elapsed_seconds
            const pct = seconds != null ? (seconds / maxSeconds) * 100 : 0
            return (
              <div key={run.id} className="dither-bar-row" role="listitem">
                <div className="dither-bar-label">
                  <span
                    className="series-dot"
                    style={{ background: pairColors[run.id] }}
                  />
                  <span>{run.name}</span>
                </div>
                <div className="dither-bar-track">
                  {seconds != null && (
                    <div
                      className="dither-bar-fill"
                      style={{
                        width: `${Math.max(pct, 2)}%`,
                        backgroundColor: pairColors[run.id],
                      }}
                    />
                  )}
                </div>
                <div className="dither-bar-value">
                  {seconds != null ? duration(seconds) : <span className="missing-value">—</span>}
                </div>
              </div>
            )
          })}
        </div>
      </MetricPanel>

      <MetricPanel
        title="Tokens"
        unit="Count"
        detail="Total input tokens, including cache reads and writes, plus output tokens across requests. Cached input is counted once per request. Missing final usage summaries are left unreported."
        footer="Input (including cache) + output"
      >
        <div className="dither-bar-list" role="list">
          {runs.map((run) => {
            const tokens = run.usage?.tokens
            const pct = tokens != null ? (tokens / maxTokens) * 100 : 0
            return (
              <div key={run.id} className="dither-bar-row" role="listitem">
                <div className="dither-bar-label">
                  <span
                    className="series-dot"
                    style={{ background: pairColors[run.id] }}
                  />
                  <span>{run.name}</span>
                </div>
                <div className="dither-bar-track">
                  {tokens != null && (
                    <div
                      className="dither-bar-fill"
                      style={{
                        width: `${Math.max(pct, 2)}%`,
                        backgroundColor: pairColors[run.id],
                      }}
                    />
                  )}
                </div>
                <div className="dither-bar-value">
                  {tokens != null ? (
                    <Tooltip>
                      <TooltipTrigger
                        className="token-value-trigger"
                        aria-label={`${run.name}: ${exact.format(tokens)} tokens.`}
                      >
                        <span>{count.format(tokens)}</span>
                      </TooltipTrigger>
                      <TooltipContent className="flex-col items-start leading-relaxed">
                        <strong>{exact.format(tokens)} tokens</strong>
                        <span>{run.usage?.source}</span>
                        {run.usage?.cached_tokens != null && (
                          <span>
                            {exact.format(run.usage.cached_tokens)} cached input tokens
                          </span>
                        )}
                        <span>{run.usage?.basis}</span>
                      </TooltipContent>
                    </Tooltip>
                  ) : (
                    <span className="missing-value">—</span>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </MetricPanel>
    </div>
  )
}
