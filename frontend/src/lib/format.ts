export function formatPercent(value?: number | null) {
  if (value === null || value === undefined || Number.isNaN(value)) return "--";
  return `${(value * 100).toFixed(1)}%`;
}

export function formatDuration(ms?: number | null) {
  if (ms === null || ms === undefined) return "--";
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}

export function truncate(text: string, max = 88) {
  if (text.length <= max) return text;
  return `${text.slice(0, max)}…`;
}
