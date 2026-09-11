import type { ReactNode } from "react"
import { Info } from "lucide-react"
import { Bar, BarChart, CartesianGrid, LabelList, XAxis, YAxis } from "recharts"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
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
const chartConfig = {
  seconds: { label: "Elapsed time", color: "#e0e1e5" },
} satisfies ChartConfig

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
  const data = runs.map((run) => ({
    name: run.name,
    seconds: run.elapsed_seconds,
    fill: pairColors[run.id],
  }))
  const max = Math.max(
    60,
    ...runs.flatMap((run) => [run.elapsed_seconds ?? 0, run.limit_seconds ?? 0])
  )
  // Round subsecond deadline overshoot so a 75-minute run keeps a 75-minute axis.
  const end = Math.ceil(Math.round(max) / 300) * 300
  const missingTime = runs
    .filter((run) => run.elapsed_seconds === null)
    .map((run) => run.name)
  return (
    <div className="metrics-grid">
      <MetricPanel
        title="Cost"
        unit="USD"
        footer="Cost was not recorded for these runs."
      >
        <dl className="metric-rows">
          {runs.map((run) => (
            <div key={run.id} className="metric-row">
              <dt>
                <span
                  className="series-dot"
                  style={{ background: pairColors[run.id] }}
                />
                {run.name}
              </dt>
              <dd className="missing-value">
                {run.cost_usd === null
                  ? "—"
                  : run.cost_usd.toLocaleString("en-US", {
                      style: "currency",
                      currency: "USD",
                    })}
              </dd>
            </div>
          ))}
        </dl>
      </MetricPanel>
      <MetricPanel
        title="Tokens"
        detail="Native CLI totals use different cache accounting. Codex includes cached input; Cursor and Antigravity report cache reads separately. These totals are not directly comparable."
        footer="Native totals · cache accounting varies"
      >
        <dl className="metric-rows">
          {runs.map((run) => (
            <div key={run.id} className="metric-row token-row">
              <dt>
                <span
                  className="series-dot"
                  style={{ background: pairColors[run.id] }}
                />
                {run.name}
              </dt>
              <dd>
                {run.usage?.tokens != null ? (
                  <Tooltip>
                    <TooltipTrigger
                      className="token-value"
                      aria-label={`${run.name}: ${exact.format(run.usage.tokens)} tokens. ${run.usage.basis}.`}
                    >
                      <span>{count.format(run.usage.tokens)}</span>
                      <small>
                        {run.id === "codex"
                          ? "including cache"
                          : "plus cache reads"}
                      </small>
                    </TooltipTrigger>
                    <TooltipContent className="flex-col items-start leading-relaxed">
                      <strong>{exact.format(run.usage.tokens)} tokens</strong>
                      <span>{run.usage.source}</span>
                      {run.usage.cached_tokens !== null && (
                        <span>
                          {exact.format(run.usage.cached_tokens)} cached input
                          tokens
                        </span>
                      )}
                      <span>{run.usage.basis}</span>
                    </TooltipContent>
                  </Tooltip>
                ) : (
                  <span className="missing-value" aria-label="Not recorded">
                    —
                  </span>
                )}
              </dd>
            </div>
          ))}
        </dl>
      </MetricPanel>
      <MetricPanel
        title="Wall clock"
        unit="Minutes"
        footer={
          missingTime.length
            ? `No elapsed time recorded for ${missingTime.join(", ")}.`
            : "Elapsed time per run"
        }
      >
        <ChartContainer
          config={chartConfig}
          className="time-chart"
          aria-label={`Elapsed time. ${runs.map((run) => `${run.name}: ${duration(run.elapsed_seconds)}`).join(". ")}`}
        >
          <BarChart
            accessibilityLayer
            data={data}
            layout="vertical"
            margin={{ left: -18, right: 52, top: 4, bottom: 0 }}
            barSize={12}
          >
            <CartesianGrid horizontal={false} strokeDasharray="2 5" />
            <XAxis
              type="number"
              dataKey="seconds"
              domain={[0, end]}
              ticks={[0, end / 3, (end * 2) / 3, end]}
              tickFormatter={(value) => `${Math.round(Number(value) / 60)}`}
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 9 }}
              tickMargin={10}
            />
            <YAxis
              type="category"
              dataKey="name"
              width={90}
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 10 }}
              tickMargin={8}
            />
            <ChartTooltip
              cursor={false}
              content={
                <ChartTooltipContent
                  hideLabel
                  formatter={(value, _name, item) => (
                    <>
                      <span>{item.payload.name}</span>
                      <strong className="ml-3 font-normal tabular-nums">
                        {duration(Number(value))}
                      </strong>
                    </>
                  )}
                />
              }
            />
            <Bar
              dataKey="seconds"
              radius={[0, 3, 3, 0]}
              isAnimationActive={false}
            >
              <LabelList
                dataKey="seconds"
                position="right"
                offset={8}
                fill="#bfc1c8"
                fontSize={9}
                formatter={(value) =>
                  value == null ? "—" : duration(Number(value))
                }
              />
            </Bar>
          </BarChart>
        </ChartContainer>
      </MetricPanel>
    </div>
  )
}
