import { api } from './client';
import type { Page, SourceRecord } from '../types/models';

export const recordApi = {
  list: (query: { source_system?: string; query?: string; page?: number; page_size?: number }) => {
    const params = new URLSearchParams();
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined && value !== '') params.set(key, String(value));
    });
    const suffix = params.toString();
    return api.get<Page<SourceRecord>>(`/records${suffix ? `?${suffix}` : ''}`);
  },
  detail: (id: string) => api.get<SourceRecord>(`/records/${id}`),
};
