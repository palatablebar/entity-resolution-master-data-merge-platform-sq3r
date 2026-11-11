import { useEffect, useState } from 'react';
import { runApi } from '../api/runs';
import type { Run } from '../types/models';

/** 运行中/排队中时 1.5s 轮询一次；结束后自动停止。 */
export const useRunPolling = (run: Run | null, onChange?: (run: Run) => void) => {
  const [liveRun, setLiveRun] = useState<Run | null>(run);

  useEffect(() => {
    setLiveRun(run);
  }, [run]);

  useEffect(() => {
    if (!liveRun || (liveRun.status !== 'queued' && liveRun.status !== 'running')) return;
    let cancelled = false;
    const timer = window.setInterval(async () => {
      try {
        const next = await runApi.detail(liveRun.id);
        if (cancelled) return;
        setLiveRun(next);
        onChange?.(next);
      } catch {
        /* 轮询失败忽略，下一轮再试 */
      }
    }, 1500);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [liveRun?.id, liveRun?.status]);

  return liveRun;
};
