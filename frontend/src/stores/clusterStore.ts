import { create } from 'zustand';
import { clusterApi } from '../api/clusters';
import type { Cluster, Page } from '../types/models';

interface ClusterQuery {
  run_id?: string;
  status?: string;
  page?: number;
  page_size?: number;
}

interface ClusterState {
  data: Page<Cluster> | null;
  detail: Cluster | null;
  loading: boolean;
  error: string | null;
  load: (query: ClusterQuery) => Promise<void>;
  loadDetail: (id: string) => Promise<void>;
}

export const useClusterStore = create<ClusterState>((set) => ({
  data: null,
  detail: null,
  loading: false,
  error: null,
  load: async (query) => {
    set({ loading: true, error: null });
    try {
      const data = await clusterApi.list(query);
      set({ data, loading: false });
    } catch (error) {
      set({ loading: false, error: error instanceof Error ? error.message : '簇加载失败' });
    }
  },
  loadDetail: async (id) => {
    try {
      set({ detail: await clusterApi.detail(id) });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : '簇详情加载失败' });
    }
  },
}));
