import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { runApi } from '../api/runs';
import { EmptyState } from '../components/common/EmptyState';
import { FieldProvenance } from '../components/common/FieldProvenance';
import { StatusStamp } from '../components/common/StatusStamp';
import { useAuthGuard } from '../hooks/useAuthGuard';
import { useAuthStore } from '../stores/authStore';
import { useGoldenStore } from '../stores/goldenStore';
import { useRunStore } from '../stores/runStore';
import type { Run } from '../types/models';
import { toHumanMessage } from '../utils/errorMessage';
import { formatScore } from '../utils/formatScore';

const PAGE_SIZE = 12;

export const GoldenPage = () => {
  useAuthGuard();
  const canExport = useAuthStore((state) => state.can)('golden:export');
  const activeRunId = useRunStore((state) => state.activeRunId);
  const setActiveRun = useRunStore((state) => state.setActiveRun);
  const [searchParams] = useSearchParams();
  const clusterFilter = searchParams.get('cluster') ?? '';

  const [runs, setRuns] = useState<Run[]>([]);
  const [runId, setRunId] = useState<string | undefined>(activeRunId ?? undefined);
  const [status, setStatus] = useState('');
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(1);
  const pageData = useGoldenStore((state) => state.data);
  const detail = useGoldenStore((state) => state.detail);
  const exporting = useGoldenStore((state) => state.exporting);
  const loadGoldenPage = useGoldenStore((state) => state.load);
  const loadGoldenDetail = useGoldenStore((state) => state.loadDetail);
  const exportGoldenCsv = useGoldenStore((state) => state.exportCsv);
  const storeError = useGoldenStore((state) => state.error);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const data = await runApi.list({ page_size: 20 });
        setRuns(data.items);
        if (!runId) {
          const preferred = data.items.find((item) => item.status === 'succeeded') ?? data.items[0];
          if (preferred) {
            setRunId(preferred.id);
            setActiveRun(preferred.id);
          }
        }
      } catch (err) {
        setError(toHumanMessage(err));
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const load = useCallback(async () => {
    await loadGoldenPage({
      run_id: runId,
      status,
      query,
      cluster_id: clusterFilter || undefined,
      page,
      page_size: PAGE_SIZE,
    });
    const items = useGoldenStore.getState().data?.items ?? [];
    setSelectedId((current) => {
      if (current && items.some((item) => item.id === current)) return current;
      return items[0]?.id ?? null;
    });
  }, [runId, status, query, page, clusterFilter, loadGoldenPage]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (selectedId) void loadGoldenDetail(selectedId);
  }, [selectedId, loadGoldenDetail]);

  return (
    <div className="enter">
      <div className="page-head">
        <div>
          <div className="page-kicker">案卷 03 · 黄金档案</div>
          <h1 className="page-title">字段级仲裁结果</h1>
        </div>
        <div className="page-note">
          每个字段取 reliability 最高的来源：来源权重 × 字段完整度 × 时间衰减（30 天半衰期）。
          不确定性不隐藏：冲突字段与落选候选都留在档案里。
        </div>
        <div className="head-actions">
          <label className="field" style={{ marginBottom: 0, minWidth: 230 }}>
            <span className="field-label">运行批次</span>
            <select
              value={runId ?? ''}
              onChange={(event) => {
                setRunId(event.target.value);
                setActiveRun(event.target.value);
                setPage(1);
              }}
            >
              {runs.map((run) => (
                <option key={run.id} value={run.id}>
                  {run.run_label}
                </option>
              ))}
            </select>
          </label>
          <label className="field" style={{ marginBottom: 0 }}>
            <span className="field-label">状态</span>
            <select
              value={status}
              onChange={(event) => {
                setStatus(event.target.value);
                setPage(1);
              }}
            >
              <option value="">全部</option>
              <option value="active">生效</option>
              <option value="provisional">暂定</option>
              <option value="retired">已退役</option>
            </select>
          </label>
          <label className="field" style={{ marginBottom: 0 }}>
            <span className="field-label">档案号</span>
            <input
              value={query}
              placeholder="KH-..."
              onChange={(event) => {
                setQuery(event.target.value);
                setPage(1);
              }}
              style={{ width: 130 }}
            />
          </label>
          <button
            className="btn primary"
            disabled={!canExport || exporting}
            onClick={() => void exportGoldenCsv(runId)}
          >
            {exporting ? '导出中…' : '导出 CSV'}
          </button>
        </div>
      </div>

      {(error ?? storeError) ? (
        <div className="notice error" style={{ marginBottom: 14 }}>{error ?? storeError}</div>
      ) : null}
      {clusterFilter ? (
        <div className="notice" style={{ marginBottom: 14 }}>
          正在查看指定簇的黄金档案。清除筛选请回到{' '}
          <a href="/golden" style={{ color: 'var(--vermilion)', textDecoration: 'underline' }}>
            全部档案
          </a>
          。
        </div>
      ) : null}

      <div className="split reverse">
        <div className="paper-card">
          <div className="card-head">
            <span className="card-title">档案索引</span>
            <span className="card-caption">共 {pageData?.total ?? 0} 份</span>
          </div>
          {pageData && pageData.items.length === 0 ? (
            <EmptyState title="还没有黄金档案" hint="先发起一次解析运行，或放宽状态筛选。" />
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>档案号</th>
                  <th>姓名</th>
                  <th>手机</th>
                  <th>置信度</th>
                  <th>状态</th>
                </tr>
              </thead>
              <tbody>
                {(pageData?.items ?? []).map((item) => (
                  <tr
                    key={item.id}
                    className={`clickable${item.id === selectedId ? ' selected' : ''}`}
                    onClick={() => setSelectedId(item.id)}
                  >
                    <td className="mono">{item.entity_key}</td>
                    <td>{item.display?.name ?? item.fields?.find((f) => f.field === 'name')?.value ?? '—'}</td>
                    <td className="mono">
                      {item.display?.phone ?? item.fields?.find((f) => f.field === 'phone')?.value ?? '—'}
                    </td>
                    <td className="num">{formatScore(item.confidence)}</td>
                    <td>
                      <StatusStamp kind="golden" value={item.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <div className="pager">
            <button className="btn ghost" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>
              ← 上一页
            </button>
            <span className="num">
              {pageData?.page ?? 1} / {pageData?.total_pages ?? 1}
            </span>
            <button
              className="btn ghost"
              disabled={!pageData || pageData.page >= pageData.total_pages}
              onClick={() => setPage((value) => value + 1)}
            >
              下一页 →
            </button>
          </div>
        </div>

        <div>
          {detail ? (
            <div className="paper-card">
              <div className="card-head">
                <span className="card-title">{detail.entity_key}</span>
                <StatusStamp kind="golden" value={detail.status} />
                {detail.conflict_fields.length > 0 ? (
                  <span className="stamp press">冲突 {detail.conflict_fields.length}</span>
                ) : null}
                <span className="card-caption" style={{ marginLeft: 'auto' }}>
                  簇置信度 {formatScore(detail.confidence)}
                </span>
              </div>
              {detail.cluster ? (
                <div className="dim" style={{ fontSize: 12 }}>
                  {detail.cluster.record_count} 条来源记录 · {detail.cluster.member_keys.join(' / ')}
                </div>
              ) : null}
              <div style={{ marginTop: 10 }}>
                <FieldProvenance fields={detail.fields} />
              </div>
              <div className="formula" style={{ marginTop: 12 }}>
                reliability = 来源权重 × 字段完整度 × 0.5^(距来源更新天数 / 30)
              </div>
            </div>
          ) : (
            <div className="paper-card">
              <EmptyState title="选择左侧一份档案" hint="这里会展示每个字段为什么取这个值、落选了谁。" />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
