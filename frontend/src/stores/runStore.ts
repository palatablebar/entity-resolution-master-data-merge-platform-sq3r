import { create } from 'zustand';
import { metaApi } from '../api/meta';
import type { Overview, Run } from '../types/models';

interface RunState {
  overview: Overview | null;
  activeRunId: string | null;
  loading: boolean;
  refresh: () => Promise<void>;
  setActiveRun: (runId: string | null) => void;
  adoptLatestRun: (run: Run) => void;
}

export const useRunStore = create<RunState>((set, get) => ({
  overview: null,
  activeRunId: null,
  loading: false,
  refresh: async () => {
    set({ loading: true });
    try {
      const overview = await metaApi.overview();
      const current = get().activeRunId;
      set({
        overview,
        activeRunId: current ?? overview.latest_run?.id ?? null,
        loading: false,
      });
    } catch {
      set({ loading: false });
    }
  },
  setActiveRun: (runId) => set({ activeRunId: runId }),
  adoptLatestRun: (run) => set({ activeRunId: run.id }),
}));
