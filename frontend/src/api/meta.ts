import { api } from './client';
import type { Overview } from '../types/models';

export const metaApi = {
  overview: () => api.get<Overview>('/meta/overview'),
};
