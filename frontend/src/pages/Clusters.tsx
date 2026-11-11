import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { runApi } from '../api/runs';
import { EmptyState } from '../components/common/EmptyState';
import { StatusStamp } from '../components/common/StatusStamp';
import { SOURCE_LABELS } from '../constants/resolution';
import { useAuthGuard } from '../hooks/useAuthGuard';
import { useClusterStore } from '../stores/clusterStore';
import { useRunStore } from '../stores/runStore';
import type { Run } from '../types/models';
import { toHumanMessage } from '../utils/errorMessage';
import { formatScore } from '../utils/formatScore';

const PAGE_SIZE = 10;

export const ClustersPage = () => {
  useAuthGuard();
  const navigate = useNavigate();
  const activeRunId = useRunStore((state) => state.activeRunId);
  const setActiveRun = useRunStore((state) => state.setActiveRun);

  const [runs, setRuns] = useState<Run[]>([]);
  const [runId, setRunId] = useState<string | undefined>(activeRunId ?? undefined);
  const [status, setStatus] = useState('');
  const [page, setPage] = useState(1);
  const pageData = useClusterStore((state) => state.data);
  const detail = useClusterStore((state) => state.detail);
  const loadClusterPage = useClusterStore((state) => state.load);
  const loadClusterDetail = useClusterStore((state) => state.loadDetail);
  const storeError = useClusterStore((state) => state.error);
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
    await loadClusterPage({ run_id: runId, status, page, page_size: PAGE_SIZE });
    const items = useClusterStore.getState().data?.items ?? [];
    setSelectedId((current) => {
      if (current && items.some((item) => item.id === current)) return current;
      return items[0]?.id ?? null;
    });
  }, [runId, status, page, loadClusterPage]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (selectedId) void loadClusterDetail(selectedId);
  }, [selectedId, loadClusterDetail]);

  const counts = useMemo(() => {
    const items = pageData?.items ?? [];
    return {
      auto: items.filter((item) => item.status === 'auto_merged').length,
      review: items.filter((item) => item.status === 'pending_review').length,
      confirmed: items.filter((item) => item.status === 'confirmed').length,
    };
  }, [pageData]);

  return (
    <div className="enter">
      <div className="page-head">
        <div>
          <div className="page-kicker">案卷 02 · 实体簇</div>
          <h1 className="page-title">成簇图册</h1>
        </div>
        <div className="page-note">
          auto 边用并查集直接连通成簇；review 边只结成待复核簇，不自动连通。
          簇置信度取簇内最小边分——最弱一环决定这簇值不值得信。
        </div>
        <div className="head-actions">
          <label className="field" style={{ marginBottom: 0, minWidth: 250 }}>
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
            <span className="field-label">簇状态</span>
            <select
              value={status}
              onChange={(event) => {
                setStatus(event.target.value);
                setPage(1);
              }}
            >
              <option value="">全部</option>
              <option value="auto_merged">自动成簇</option>
              <option value="pending_review">待复核</option>
              <option value="confirmed">已确认</option>
            </select>
          </label>
        </div>
      </div>

      {(error ?? storeError) ? (
        <div className="notice error" style={{ marginBottom: 14 }}>{error ?? storeError}</div>
      ) : null}

      <div className="split">
        <div className="paper-card">
          <div className="card-head">
            <span className="card-title">簇清单</span>
            <span className="card-caption">
              共 {pageData?.total ?? 0} 簇 · 本页 自动 {counts.auto} / 待复核 {counts.review} / 已确认 {counts.confirmed}
            </span>
          </div>
          {pageData && pageData.items.length === 0 ? (
            <EmptyState title="该批次没有簇" hint="可能阈值过紧导致没有 auto 边；到运行报告重跑或放宽阈值。" />
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>簇键</th>
                  <th>记录数</th>
                  <th>置信度</th>
                  <th>状态</th>
                  <th>类型</th>
                </tr>
              </thead>
              <tbody>
                {(pageData?.items ?? []).map((item) => (
                  <tr
                    key={item.id}
                    className={`clickable${item.id === selectedId ? ' selected' : ''}`}
                    onClick={() => setSelectedId(item.id)}
                  >
                    <td className="mono">{item.cluster_key.slice(0, 10)}</td>
                    <td className="num">{item.record_count}</td>
                    <td className="num">{formatScore(item.confidence)}</td>
                    <td>
                      <StatusStamp kind="cluster" value={item.status} />
                    </td>
                    <td className="dim">{item.edge_type === 'auto' ? '自动边' : '复核边'}</td>
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
                <span className="card-title">簇详情</span>
                <StatusStamp kind="cluster" value={detail.status} />
                <span className="card-caption" style={{ marginLeft: 'auto' }}>
                  {detail.record_count} 条来源记录
                </span>
              </div>
              <div className="metric-row">
                <div className="metric">
                  <div className="metric-label">簇置信度</div>
                  <div className="metric-value">{formatScore(detail.confidence)}</div>
                </div>
                <div className="metric">
                  <div className="metric-label">簇键</div>
                  <div className="mono soft" style={{ paddingTop: 8 }}>{detail.cluster_key}</div>
                </div>
              </div>

              <div className="paper-label" style={{ marginTop: 14 }}>成员记录</div>
              <table className="table" style={{ marginTop: 6 }}>
                <thead>
                  <tr>
                    <th>来源</th>
                    <th>姓名</th>
                    <th>手机</th>
                    <th>地址</th>
                  </tr>
                </thead>
                <tbody>
                  {(detail.members ?? []).map((member) => (
                    <tr key={member.id}>
                      <td>
                        <div className="soft">{member.source_label}</div>
                        <div className="mono dim">{member.external_id}</div>
                      </td>
                      <td>{member.full_name ?? '—'}</td>
                      <td className="mono">{member.phone ?? '—'}</td>
                      <td className="truncate" title={member.address ?? ''}>
                        {member.address ?? '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              <div className="paper-label" style={{ marginTop: 16 }}>簇内候选边</div>
              <table className="table" style={{ marginTop: 6 }}>
                <thead>
                  <tr>
                    <th>分数</th>
                    <th>判定</th>
                    <th>复核状态</th>
                  </tr>
                </thead>
                <tbody>
                  {(detail.edges ?? []).map((edge) => (
                    <tr key={edge.id}>
                      <td className="num">{formatScore(edge.score)}</td>
                      <td>
                        <StatusStamp kind="decision" value={edge.decision} />
                      </td>
                      <td className="dim">
                        {edge.status === 'pending' ? '未处理' : edge.status === 'confirmed' ? '已确认' : '已拒绝'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              <div className="btn-row" style={{ marginTop: 16 }}>
                <button
                  className="btn primary"
                  onClick={() => navigate(`/golden?cluster=${detail.id}`)}
                >
                  查看该簇黄金档案
                </button>
                <span className="dim" style={{ fontSize: 12 }}>
                  成员来源：{Array.from(new Set((detail.members ?? []).map((m) => SOURCE_LABELS[m.source_system]))).join('、')}
                </span>
              </div>
            </div>
          ) : (
            <div className="paper-card">
              <EmptyState title="选择左侧一个簇" hint="详情会列出成员记录、簇内候选边与置信度。" />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
