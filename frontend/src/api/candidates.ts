import { api } from './client';
import type { Candidate, Page } from '../types/models';

interface CandidateQuery {
  run_id?: string;
  decision?: string;
  status?: string;
  page?: number;
  page_size?: number;
}

export const candidateApi = {
  list: (query: CandidateQuery) => {
    const params = new URLSearchParams();
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined && value !== '') params.set(key, String(value));
    });
    const suffix = params.toString();
    return api.get<Page<Candidate>>(`/candidates${suffix ? `?${suffix}` : ''}`);
  },
  detail: (id: string) => api.get<Candidate>(`/candidates/${id}`),
  review: (id: string, action: 'confirm' | 'reject', note: string) =>
    api.post<Candidate>(`/candidates/${id}/review`, { action, note }),
};
