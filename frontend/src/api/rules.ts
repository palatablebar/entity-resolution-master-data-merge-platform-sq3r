import { api } from './client';
import type { MergeRule } from '../types/models';

export interface RuleUpdate {
  field_weights?: Record<string, number>;
  source_reliability?: Record<string, number>;
  auto_threshold?: number;
  review_threshold?: number;
  is_active?: boolean;
}

export const ruleApi = {
  list: () => api.get<{ items: MergeRule[] }>('/rules'),
  update: (id: string, payload: RuleUpdate) => api.patch<MergeRule>(`/rules/${id}`, payload),
};
