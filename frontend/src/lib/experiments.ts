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

export type ExperimentGroup = {
  id: string
  name: string
  reference: string | null
  variants: Record<string, Experiment>
}

export const pairColors: Record<string, string> = {
  codex: "#e0e1e5",
  cursor: "#a3abc2",
  antigravity: "#c6af87",
  claude: "#d99a7e",
  kimi: "#85b8a5",
}
export const pairLetters: Record<string, string> = {
  codex: "A",
  cursor: "B",
  antigravity: "C",
  claude: "D",
  kimi: "E",
}
export const modelKey = (value: string) =>
  value.includes("gemini-3.8-flash")
    ? "gemini"
    : value.includes("gpt-5.6-luna")
      ? "luna"
      : value.replace(/^[^/]+\//, "")

export const modelName = (value: string) => {
  if (value.includes("gemini-3.8-flash")) return "Gemini 3.8 Flash High"
  if (value.includes("gpt-5.6-luna")) return "GPT 5.6 Luna High"
  return value.replace(/^[^/]+\//, "")
}
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
