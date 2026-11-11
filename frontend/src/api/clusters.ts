import { api } from './client';
import type { Cluster, Page } from '../types/models';

export const clusterApi = {
  list: (query: { run_id?: string; status?: string; page?: number; page_size?: number }) => {
    const params = new URLSearchParams();
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined && value !== '') params.set(key, String(value));
    });
    const suffix = params.toString();
    return api.get<Page<Cluster>>(`/clusters${suffix ? `?${suffix}` : ''}`);
  },
  detail: (id: string) => api.get<Cluster>(`/clusters/${id}`),
};
