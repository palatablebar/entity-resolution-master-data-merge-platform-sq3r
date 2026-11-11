import { api } from './client';
import type { AuditLog, Page, Run } from '../types/models';

export const runApi = {
  list: (query: { status?: string; page?: number; page_size?: number } = {}) => {
    const params = new URLSearchParams();
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined && value !== '') params.set(key, String(value));
    });
    const suffix = params.toString();
    return api.get<Page<Run>>(`/runs${suffix ? `?${suffix}` : ''}`);
  },
  detail: (id: string) => api.get<Run>(`/runs/${id}`),
  create: (payload: { rule_id?: string; run_label?: string }) => api.post<Run>('/runs', payload),
  rerun: (id: string) => api.post<Run>(`/runs/${id}/rerun`),
  auditLogs: () => api.get<{ items: AuditLog[] }>('/audit/logs?limit=12'),
};
