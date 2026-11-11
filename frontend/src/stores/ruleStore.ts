import { create } from 'zustand';
import { ruleApi, type RuleUpdate } from '../api/rules';
import type { MergeRule } from '../types/models';

interface RuleState {
  rules: MergeRule[];
  loading: boolean;
  saving: boolean;
  error: string | null;
  load: () => Promise<MergeRule[]>;
  save: (id: string, payload: RuleUpdate) => Promise<MergeRule | null>;
  activeRule: () => MergeRule | null;
}

export const useRuleStore = create<RuleState>((set, get) => ({
  rules: [],
  loading: false,
  saving: false,
  error: null,
  load: async () => {
    set({ loading: true, error: null });
    try {
      const data = await ruleApi.list();
      set({ rules: data.items, loading: false });
      return data.items;
    } catch (error) {
      set({ loading: false, error: error instanceof Error ? error.message : '规则加载失败' });
      return [];
    }
  },
  save: async (id, payload) => {
    set({ saving: true, error: null });
    try {
      const updated = await ruleApi.update(id, payload);
      set({
        rules: get().rules.map((rule) => (rule.id === updated.id ? updated : rule)),
        saving: false,
      });
      return updated;
    } catch (error) {
      set({ saving: false, error: error instanceof Error ? error.message : '规则保存失败' });
      return null;
    }
  },
  activeRule: () => get().rules.find((rule) => rule.is_active) ?? get().rules[0] ?? null,
}));
