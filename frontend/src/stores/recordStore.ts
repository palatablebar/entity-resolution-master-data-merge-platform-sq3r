import { create } from 'zustand';
import { recordApi } from '../api/records';

const SOURCES = ['pos', 'ecommerce', 'service'] as const;

interface RecordState {
  counts: Record<string, number>;
  total: number;
  loading: boolean;
  loadCounts: () => Promise<void>;
}

/** 来源档案总览：按来源系统各取一次 total，用于候选页顶部的档案基数。 */
export const useRecordStore = create<RecordState>((set) => ({
  counts: {},
  total: 0,
  loading: false,
  loadCounts: async () => {
    set({ loading: true });
    try {
      const results = await Promise.all(
        SOURCES.map((source) => recordApi.list({ source_system: source, page_size: 1 })),
      );
      const counts: Record<string, number> = {};
      let total = 0;
      results.forEach((page, index) => {
        counts[SOURCES[index]] = page.total;
        total += page.total;
      });
      set({ counts, total, loading: false });
    } catch {
      set({ loading: false });
    }
  },
}));
