import { Info } from "lucide-react"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { duration, type Run } from "@/lib/experiments"

const count = new Intl.NumberFormat("en-US", {
  notation: "compact",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})
const exact = new Intl.NumberFormat("en-US")
const harnessOrder = ["codex", "claude", "kimi"]

export function Metrics({ runs }: { runs: Run[] }) {
  const ordered = [...runs].sort(
    (a, b) => harnessOrder.indexOf(a.id) - harnessOrder.indexOf(b.id)
  )
  return (
    <section className="run-statistics" aria-labelledby="run-statistics-title">
      <h2 id="run-statistics-title">Run statistics</h2>
      <div className="metrics-table-wrap">
        <table className="metrics-table">
          <thead>
            <tr>
              <th scope="col">Harness</th>
              <th scope="col">Wall clock</th>
              <th scope="col">
                <span className="metrics-token-heading">
                  Tokens
                  <Tooltip>
                    <TooltipTrigger
                      aria-label="About token counts"
                      className="info-trigger"
                    >
                      <Info size={13} aria-hidden="true" />
                    </TooltipTrigger>
                    <TooltipContent className="leading-relaxed">
                      Total input tokens, including cache reads and writes, plus
                      output tokens across requests. Cached input is counted
                      once per request. Missing final usage summaries are left
                      unreported.
                    </TooltipContent>
                  </Tooltip>
                </span>
              </th>
              <th scope="col">
                <span className="metrics-token-heading">
                  Tool calls
                  <Tooltip>
                    <TooltipTrigger
                      aria-label="About tool-call counts"
                      className="info-trigger"
                    >
                      <Info size={13} aria-hidden="true" />
                    </TooltipTrigger>
                    <TooltipContent className="leading-relaxed">
                      Distinct tool calls recorded by the harness, including
                      failed calls and retries. Repeated events for the same
                      call are counted once. Tool granularity varies by harness.
                    </TooltipContent>
                  </Tooltip>
                </span>
              </th>
            </tr>
          </thead>
          <tbody>
            {ordered.map((run) => {
              const tokens = run.usage?.tokens
              return (
                <tr key={run.id}>
                  <th scope="row">{run.name}</th>
                  <td>
                    <span
                      className={
                        run.elapsed_seconds === null
                          ? "missing-value"
                          : run.status === "time_limit"
                            ? "time-limit-value"
                            : undefined
                      }
                      title={
                        run.status === "time_limit"
                          ? "Time limit reached"
                          : undefined
                      }
                      aria-label={
                        run.status === "time_limit"
                          ? `${duration(run.elapsed_seconds)} — time limit reached`
                          : undefined
                      }
                    >
                      {duration(run.elapsed_seconds)}
                    </span>
                  </td>
                  <td>
                    {tokens != null ? (
                      <Tooltip>
                        <TooltipTrigger
                          className="token-value-trigger"
                          aria-label={`${run.name}: ${exact.format(tokens)} tokens.`}
                        >
                          {count.format(tokens)}
                        </TooltipTrigger>
                        <TooltipContent className="flex-col items-start leading-relaxed">
                          <strong>{exact.format(tokens)} tokens</strong>
                          <span>{run.usage?.source}</span>
                          {run.usage?.cached_tokens != null && (
                            <span>
                              {exact.format(run.usage.cached_tokens)} cached
                              input tokens
                            </span>
                          )}
                          <span>{run.usage?.basis}</span>
                        </TooltipContent>
                      </Tooltip>
                    ) : (
                      <span
                        className="missing-value"
                        aria-label="Token count unavailable"
                      >
                        —
                      </span>
                    )}
                  </td>
                  <td>
                    {run.tool_calls != null ? (
                      exact.format(run.tool_calls)
                    ) : (
                      <span className="missing-value">—</span>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}
