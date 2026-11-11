import { create } from 'zustand';
import { goldenApi } from '../api/golden';
import type { GoldenRecord, Page } from '../types/models';
import { downloadBlob } from '../utils/downloadCsv';

interface GoldenQuery {
  run_id?: string;
  query?: string;
  status?: string;
  cluster_id?: string;
  page?: number;
  page_size?: number;
}

interface GoldenState {
  data: Page<GoldenRecord> | null;
  detail: GoldenRecord | null;
  loading: boolean;
  exporting: boolean;
  error: string | null;
  load: (query: GoldenQuery) => Promise<void>;
  loadDetail: (id: string) => Promise<void>;
  exportCsv: (runId?: string) => Promise<void>;
}

export const useGoldenStore = create<GoldenState>((set) => ({
  data: null,
  detail: null,
  loading: false,
  exporting: false,
  error: null,
  load: async (query) => {
    set({ loading: true, error: null });
    try {
      const data = await goldenApi.list(query);
      set({ data, loading: false });
    } catch (error) {
      set({ loading: false, error: error instanceof Error ? error.message : '黄金档案加载失败' });
    }
  },
  loadDetail: async (id) => {
    try {
      set({ detail: await goldenApi.detail(id) });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : '档案详情加载失败' });
    }
  },
  exportCsv: async (runId) => {
    set({ exporting: true, error: null });
    try {
      const blob = await goldenApi.exportCsv(runId);
      downloadBlob(blob, `golden_records_${(runId ?? 'latest').slice(0, 8)}.csv`);
    } catch (error) {
      set({ error: error instanceof Error ? error.message : '导出失败' });
    } finally {
      set({ exporting: false });
    }
  },
}));
