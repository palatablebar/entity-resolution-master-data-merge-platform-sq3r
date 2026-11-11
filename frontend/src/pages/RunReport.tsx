import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { runApi } from '../api/runs';
import { EmptyState } from '../components/common/EmptyState';
import { StatusStamp } from '../components/common/StatusStamp';
import { BLOCKING_KEY_LABELS, RUN_STATUS_LABELS, SCORE_BIN_LABELS } from '../constants/resolution';
import { useRunPolling } from '../hooks/useRunPolling';
import { useAuthGuard } from '../hooks/useAuthGuard';
import { useAuthStore } from '../stores/authStore';
import { useRunStore } from '../stores/runStore';
import type { AuditLog, Run } from '../types/models';
import { toHumanMessage } from '../utils/errorMessage';
import { formatDateTime, formatDuration, formatScore } from '../utils/formatScore';

export const RunReportPage = () => {
  useAuthGuard();
  const [searchParams] = useSearchParams();
  const presetRunId = searchParams.get('run');
  const canTrigger = useAuthStore((state) => state.can)('runs:trigger');
  const canAudit = useAuthStore((state) => state.can)('audit:read');
  const refreshOverview = useRunStore((state) => state.refresh);

  const [runs, setRuns] = useState<Run[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(presetRunId);
  const [detail, setDetail] = useState<Run | null>(null);
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const loadRuns = useCallback(async () => {
    try {
      const data = await runApi.list({ page_size: 20 });
      setRuns(data.items);
      setSelectedId((current) => current ?? data.items[0]?.id ?? null);
    } catch (err) {
      setError(toHumanMessage(err));
    }
  }, []);

  useEffect(() => {
    void loadRuns();
    void refreshOverview();
  }, [loadRuns, refreshOverview]);

  useEffect(() => {
    if (!selectedId) return;
    void (async () => {
      try {
        setDetail(await runApi.detail(selectedId));
      } catch (err) {
        setError(toHumanMessage(err));
      }
    })();
  }, [selectedId]);

  useEffect(() => {
    if (!canAudit) return;
    void (async () => {
      try {
        const data = await runApi.auditLogs();
        setLogs(data.items);
      } catch {
        /* 审计日志非关键路径，忽略 */
      }
    })();
  }, [canAudit, detail?.status]);

  const onChange = useCallback((next: Run) => {
    setDetail(next);
    if (next.status === 'succeeded' || next.status === 'failed') {
      void loadRuns();
      void refreshOverview();
    }
  }, [loadRuns, refreshOverview]);

  const liveRun = useRunPolling(detail, onChange);

  const trigger = async () => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const run = await runApi.create({ run_label: `人工触发 · ${new Date().toLocaleString('zh-CN', { hour12: false })}` });
      setMessage('解析任务已投递给 worker，页面会自动刷新进度。');
      setSelectedId(run.id);
      await loadRuns();
    } catch (err) {
      setError(toHumanMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const rerun = async () => {
    if (!detail) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const run = await runApi.rerun(detail.id);
      setSelectedId(run.id);
      await loadRuns();
    } catch (err) {
      setError(toHumanMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const distribution = liveRun?.distribution ?? [];
  const maxBin = useMemo(() => Math.max(1, ...distribution), [distribution]);
  const params = (liveRun?.params ?? {}) as Record<string, unknown>;

  return (
    <div className="enter">
      <div className="page-head">
        <div>
          <div className="page-kicker">案卷 05 · 运行报告</div>
          <h1 className="page-title">解析卷宗</h1>
        </div>
        <div className="page-note">
          每次运行都记录 blocking 命中、剪枝、判定分布、簇数量与耗时，并快照当时的规则参数。
          参数不同，历史运行仍按当时的尺度解释。
        </div>
        <div className="head-actions">
          <button className="btn primary" disabled={!canTrigger || busy} onClick={() => void trigger()}>
            {busy ? '投递中…' : '发起解析'}
          </button>
          <button className="btn" disabled={!canTrigger || busy || !detail} onClick={() => void rerun()}>
            按本卷参数重跑
          </button>
        </div>
      </div>

      {error ? <div className="notice error" style={{ marginBottom: 14 }}>{error}</div> : null}
      {message ? <div className="notice" style={{ marginBottom: 14 }}>{message}</div> : null}

      <div className="split reverse">
        <div className="paper-card">
          <div className="card-head">
            <span className="card-title">运行清单</span>
            <span className="card-caption">共 {runs.length} 次</span>
          </div>
          {runs.length === 0 ? (
            <EmptyState title="还没有运行记录" hint="点右上角「发起解析」，worker 会执行 blocking、打分与聚类。" />
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>批次</th>
                  <th>状态</th>
                  <th>候选</th>
                  <th>簇</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr
                    key={run.id}
                    className={`clickable${run.id === selectedId ? ' selected' : ''}`}
                    onClick={() => setSelectedId(run.id)}
                  >
                    <td>
                      <div className="truncate" title={run.run_label}>
                        {run.run_label}
                      </div>
                      <div className="dim mono" style={{ fontSize: 11 }}>
                        {formatDateTime(run.created_at)}
                      </div>
                    </td>
                    <td>
                      <StatusStamp kind="run" value={run.status} />
                    </td>
                    <td className="num">{run.candidate_pairs}</td>
                    <td className="num">
                      {run.clusters_auto}/{run.clusters_review}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div>
          {liveRun ? (
            <div className="paper-card">
              <div className="card-head">
                <span className="card-title">{liveRun.run_label}</span>
                <StatusStamp kind="run" value={liveRun.status} />
                <span className="card-caption" style={{ marginLeft: 'auto' }}>
                  耗时 {formatDuration(liveRun.duration_ms)}
                </span>
              </div>

              {liveRun.error_message ? (
                <div className="notice error" style={{ marginBottom: 12 }}>
                  {liveRun.error_code}: {liveRun.error_message}
                </div>
              ) : null}

              <div className="metric-row">
                <Metric label="扫描记录" value={liveRun.records_scanned} />
                <Metric label="blocking 命中" value={liveRun.blocked_pairs_raw} />
                <Metric label="剪枝" value={liveRun.pruned_pairs} />
                <Metric label="候选对" value={liveRun.candidate_pairs} />
              </div>
              <div className="metric-row">
                <Metric label="auto 对" value={liveRun.auto_pairs} accent />
                <Metric label="review 对" value={liveRun.review_pairs} />
                <Metric label="reject 对" value={liveRun.rejected_pairs} />
                <Metric label="黄金档案" value={liveRun.golden_records} />
              </div>
              <div className="metric-row">
                <Metric label="自动簇" value={liveRun.clusters_auto} />
                <Metric label="待复核簇" value={liveRun.clusters_review} />
                <Metric label="开始" value={formatDateTime(liveRun.started_at)} small />
                <Metric label="结束" value={formatDateTime(liveRun.finished_at)} small />
              </div>

              <div className="paper-label" style={{ marginTop: 14 }}>blocking 键</div>
              <div className="soft" style={{ fontSize: 13 }}>
                {liveRun.blocking_keys.map((key) => BLOCKING_KEY_LABELS[key] ?? key).join(' ∪ ')}
              </div>

              <div className="paper-label" style={{ marginTop: 16 }}>候选分数分布</div>
              <div className="histogram">
                {distribution.map((count, index) => (
                  <div className="histogram-col" key={index}>
                    <div
                      className={`histogram-bar${index >= 7 ? ' hot' : ''}`}
                      style={{ height: `${Math.max(2, (count / maxBin) * 100)}%` }}
                      title={`${SCORE_BIN_LABELS[index] ?? index}: ${count} 对`}
                    />
                    <div className="histogram-label">{SCORE_BIN_LABELS[index] ?? ''}</div>
                  </div>
                ))}
              </div>
              <div className="dim" style={{ fontSize: 12, marginTop: 6 }}>
                分数集中在 0.9+ 说明来源数据质量较好；0.7-0.9 的尾部就是需要人工复核的部分。
              </div>

              <div className="paper-label" style={{ marginTop: 16 }}>规则参数快照</div>
              <table className="table">
                <tbody>
                  <tr>
                    <td className="dim">规则</td>
                    <td>
                      {String(params.rule_name ?? '—')} · v{String(params.rule_version ?? '—')}
                    </td>
                  </tr>
                  <tr>
                    <td className="dim">阈值</td>
                    <td className="mono">
                      auto ≥ {formatScore(Number(params.auto_threshold ?? 0))} / review ≥{' '}
                      {formatScore(Number(params.review_threshold ?? 0))}
                    </td>
                  </tr>
                  <tr>
                    <td className="dim">字段权重</td>
                    <td className="mono">
                      {Object.entries((params.field_weights as Record<string, number>) ?? {})
                        .map(([key, value]) => `${key}:${value}`)
                        .join(' · ')}
                    </td>
                  </tr>
                  <tr>
                    <td className="dim">来源可靠性</td>
                    <td className="mono">
                      {Object.entries((params.source_reliability as Record<string, number>) ?? {})
                        .map(([key, value]) => `${key}:${value}`)
                        .join(' · ')}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          ) : (
            <div className="paper-card">
              <EmptyState title="选择左侧一次运行" hint="右侧展示命中/剪枝/判定/簇/黄金档案与参数快照。" />
            </div>
          )}

          {canAudit ? (
            <div className="paper-card tint">
              <div className="card-head">
                <span className="card-title">审计留痕</span>
                <span className="card-caption">仅 admin 可见</span>
              </div>
              {logs.length === 0 ? (
                <div className="dim" style={{ fontSize: 13 }}>暂无审计记录。</div>
              ) : (
                <table className="table">
                  <tbody>
                    {logs.map((log) => (
                      <tr key={log.id}>
                        <td className="mono" style={{ whiteSpace: 'nowrap' }}>{formatDateTime(log.created_at)}</td>
                        <td>{log.action}</td>
                        <td className="dim">{log.actor_email}</td>
                        <td className="dim mono">{log.entity_type}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
};

const Metric = ({
  label,
  value,
  accent = false,
  small = false,
}: {
  label: string;
  value: number | string;
  accent?: boolean;
  small?: boolean;
}) => (
  <div className="metric">
    <div className="metric-label">{label}</div>
    <div
      className={`metric-value${accent ? ' vermilion' : ''}`}
      style={small ? { fontSize: 13, fontWeight: 400, paddingTop: 6 } : undefined}
    >
      {value}
    </div>
  </div>
);
