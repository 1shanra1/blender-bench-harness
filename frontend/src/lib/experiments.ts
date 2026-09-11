export const axes = [
  ["positive_x", "+X"],
  ["negative_x", "−X"],
  ["positive_y", "+Y"],
  ["negative_y", "−Y"],
  ["positive_z", "+Z"],
  ["negative_z", "−Z"],
] as const

export type Axis = (typeof axes)[number][0]
export type Usage = {
  tokens: number | null
  cached_tokens: number | null
  basis: string
  source: string
}
export type Run = {
  id: string
  name: string
  model: string
  provider: string | null
  effort: string | null
  status: string
  native_complete: boolean | null
  model_url: string | null
  render: string | null
  views: Record<Axis, string | null>
  evaluation_status: string
  elapsed_seconds: number | null
  limit_seconds: number | null
  usage: Usage | null
  cost_usd: number | null
}
export type Experiment = {
  id: string
  name: string
  reference: string | null
  started_at: string | null
  runs: Run[]
}

export const pairColors: Record<string, string> = {
  codex: "#e0e1e5",
  cursor: "#a3abc2",
  antigravity: "#c6af87",
}
export const pairLetters: Record<string, string> = {
  codex: "A",
  cursor: "B",
  antigravity: "C",
}
export const modelName = (value: string) =>
  value.includes("gemini-3.8-flash")
    ? "Gemini 3.8 Flash"
    : value.replace(/^[^/]+\//, "")
export function duration(seconds: number | null) {
  if (seconds === null) return "—"
  const rounded = Math.round(seconds)
  return `${Math.floor(rounded / 60)}m ${String(rounded % 60).padStart(2, "0")}s`
}
export function runStatus(run: Run) {
  if (run.status === "time_limit") return "Time limit"
  if (run.status.endsWith("failed")) return "Run failed"
  if (run.native_complete === true) return "Goal complete"
  if (run.status === "stopped") return "Stopped"
  return "Outcome unavailable"
}
