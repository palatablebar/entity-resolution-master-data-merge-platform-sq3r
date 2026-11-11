import { create } from 'zustand';
import { candidateApi } from '../api/candidates';
import type { Candidate, Page } from '../types/models';

interface CandidateQuery {
  run_id?: string;
  decision?: string;
  status?: string;
  page?: number;
  page_size?: number;
}

interface CandidateState {
  data: Page<Candidate> | null;
  loading: boolean;
  error: string | null;
  load: (query: CandidateQuery) => Promise<Page<Candidate> | null>;
  applyReviewed: (candidate: Candidate) => void;
}

/** 候选对列表状态：筛选/分页在页面，取数与缓存放 store。 */
export const useCandidateStore = create<CandidateState>((set, get) => ({
  data: null,
  loading: false,
  error: null,
  load: async (query) => {
    set({ loading: true, error: null });
    try {
      const data = await candidateApi.list(query);
      set({ data, loading: false });
      return data;
    } catch (error) {
      set({ loading: false, error: error instanceof Error ? error.message : '候选加载失败' });
      return null;
    }
  },
  applyReviewed: (candidate) => {
    const data = get().data;
    if (!data) return;
    set({
      data: {
        ...data,
        items: data.items.map((item) => (item.id === candidate.id ? candidate : item)),
      },
    });
  },
}));
