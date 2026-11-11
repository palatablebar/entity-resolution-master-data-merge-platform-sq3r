import { api } from './client';
import type { GoldenRecord, Page } from '../types/models';

export const goldenApi = {
  list: (query: {
    run_id?: string;
    query?: string;
    status?: string;
    cluster_id?: string;
    page?: number;
    page_size?: number;
  }) => {
    const params = new URLSearchParams();
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined && value !== '') params.set(key, String(value));
    });
    const suffix = params.toString();
    return api.get<Page<GoldenRecord>>(`/golden${suffix ? `?${suffix}` : ''}`);
  },
  detail: (id: string) => api.get<GoldenRecord>(`/golden/${id}`),
  exportCsv: (runId?: string) =>
    api.getBlob(`/golden/export${runId ? `?run_id=${runId}` : ''}`),
};
