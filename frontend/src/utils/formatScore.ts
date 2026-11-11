export const formatScore = (value: number | null | undefined): string =>
  value === null || value === undefined ? '—' : value.toFixed(3);

export const formatPercent = (value: number | null | undefined): string =>
  value === null || value === undefined ? '—' : `${(value * 100).toFixed(1)}%`;

export const formatDuration = (ms: number): string =>
  ms >= 1000 ? `${(ms / 1000).toFixed(2)}s` : `${ms}ms`;

export const formatDateTime = (iso: string | null | undefined): string => {
  if (!iso) return '—';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString('zh-CN', { hour12: false });
};
