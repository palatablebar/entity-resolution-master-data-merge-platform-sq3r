import { useCallback, useEffect, useMemo, useState } from 'react';
import { candidateApi } from '../api/candidates';
import { runApi } from '../api/runs';
import { EmptyState } from '../components/common/EmptyState';
import { RecordDiff } from '../components/common/RecordDiff';
import { ScoreBreakdown } from '../components/common/ScoreBreakdown';
import { StatusStamp } from '../components/common/StatusStamp';
import { BLOCKING_KEY_LABELS, CANDIDATE_STATUS_LABELS, DECISION_LABELS } from '../constants/resolution';
import { useAuthGuard } from '../hooks/useAuthGuard';
import { useAuthStore } from '../stores/authStore';
import { useCandidateStore } from '../stores/candidateStore';
import { useRecordStore } from '../stores/recordStore';
import { useRunStore } from '../stores/runStore';
import type { Candidate, Run } from '../types/models';
import { toHumanMessage } from '../utils/errorMessage';
import { formatScore } from '../utils/formatScore';

const PAGE_SIZE = 12;

export const CandidatesPage = () => {
  useAuthGuard();
  const user = useAuthStore((state) => state.user);
  const canReview = useAuthStore((state) => state.can)('candidates:review');
  const activeRunId = useRunStore((state) => state.activeRunId);
  const setActiveRun = useRunStore((state) => state.setActiveRun);
  const refreshOverview = useRunStore((state) => state.refresh);

  const [runs, setRuns] = useState<Run[]>([]);
  const [runId, setRunId] = useState<string | undefined>(activeRunId ?? undefined);
  const [decision, setDecision] = useState('review');
  const [status, setStatus] = useState('pending');
  const [page, setPage] = useState(1);
  const pageData = useCandidateStore((state) => state.data);
  const loadCandidatePage = useCandidateStore((state) => state.load);
  const recordCounts = useRecordStore((state) => state.counts);
  const recordTotal = useRecordStore((state) => state.total);
  const loadRecordCounts = useRecordStore((state) => state.loadCounts);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<Candidate | null>(null);
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    void loadRecordCounts();
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

  const loadCandidates = useCallback(async () => {
    const data = await loadCandidatePage({
      run_id: runId,
      decision,
      status,
      page,
      page_size: PAGE_SIZE,
    });
    if (!data) return;
    setSelectedId((current) => {
      if (current && data.items.some((item) => item.id === current)) return current;
      return data.items[0]?.id ?? null;
    });
  }, [runId, decision, status, page, loadCandidatePage]);

  useEffect(() => {
    void loadCandidates();
  }, [loadCandidates]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    void (async () => {
      try {
        setDetail(await candidateApi.detail(selectedId));
      } catch (err) {
        setError(toHumanMessage(err));
      }
    })();
  }, [selectedId]);

  const currentRun = useMemo(() => runs.find((item) => item.id === runId) ?? null, [runs, runId]);

  const review = async (action: 'confirm' | 'reject') => {
    if (!detail) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await candidateApi.review(detail.id, action, note);
      setMessage(action === 'confirm' ? '已确认合并，簇与黄金档案同步更新。' : '已拒绝合并，候选留档。');
      setNote('');
      await loadCandidates();
      await refreshOverview();
      setDetail(await candidateApi.detail(detail.id));
    } catch (err) {
      setError(toHumanMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const canAct = canReview && detail?.decision === 'review' && detail?.status === 'pending';

  return (
    <div className="enter">
      <div className="page-head">
        <div>
          <div className="page-kicker">案卷 01 · 候选对复核</div>
          <h1 className="page-title">并置鉴定台</h1>
        </div>
        <div className="page-note">
          左侧是按分数排序的可疑对；右侧把两侧原始值并排铺开，逐字段看相似度、权重与贡献。
          只有 review 区间（0.75–0.92）且未处理的候选需要人工落章。
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
            <span className="field-label">判定</span>
            <select
              value={decision}
              onChange={(event) => {
                setDecision(event.target.value);
                setPage(1);
              }}
            >
              <option value="">全部</option>
              <option value="auto">自动合并</option>
              <option value="review">待复核</option>
              <option value="reject">拒绝</option>
            </select>
          </label>
          <label className="field" style={{ marginBottom: 0 }}>
            <span className="field-label">复核状态</span>
            <select
              value={status}
              onChange={(event) => {
                setStatus(event.target.value);
                setPage(1);
              }}
            >
              <option value="">全部</option>
              <option value="pending">未处理</option>
              <option value="confirmed">已确认</option>
              <option value="rejected">已拒绝</option>
            </select>
          </label>
        </div>
      </div>

      <div className="dim" style={{ fontSize: 12, marginBottom: 12 }}>
        来源档案基数：POS {recordCounts.pos ?? '—'} · 电商 {recordCounts.ecommerce ?? '—'} · 客服{' '}
        {recordCounts.service ?? '—'}（共 {recordTotal} 条，来自 /api/records 三源统计）
      </div>

      {error ? <div className="notice error" style={{ marginBottom: 14 }}>{error}</div> : null}
      {message ? <div className="notice" style={{ marginBottom: 14 }}>{message}</div> : null}
      {!canReview ? (
        <div className="notice" style={{ marginBottom: 14 }}>
          当前角色（{user?.role}）为只读，可以查看候选与证据，但不能确认或拒绝。
        </div>
      ) : null}

      <div className="split">
        <div className="paper-card">
          <div className="card-head">
            <span className="card-title">候选清单</span>
            <span className="card-caption">
              {currentRun ? currentRun.run_label : '全部运行'} · 共 {pageData?.total ?? 0} 对
            </span>
          </div>
          {pageData && pageData.items.length === 0 ? (
            <EmptyState title="当前筛选下没有候选" hint="试试把判定切到「待复核」，或发起一次新的解析运行。" />
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>分数</th>
                  <th>判定</th>
                  <th>左侧</th>
                  <th>右侧</th>
                  <th>状态</th>
                  <th>命中键</th>
                </tr>
              </thead>
              <tbody>
                {(pageData?.items ?? []).map((item) => (
                  <tr
                    key={item.id}
                    className={`clickable${item.id === selectedId ? ' selected' : ''}`}
                    onClick={() => setSelectedId(item.id)}
                  >
                    <td className="num" style={{ color: 'var(--vermilion)', fontWeight: 600 }}>
                      {formatScore(item.score)}
                    </td>
                    <td>
                      <StatusStamp kind="decision" value={item.decision} />
                    </td>
                    <td>
                      <div>{item.left?.full_name ?? '—'}</div>
                      <div className="dim mono">{item.left?.phone ?? item.left?.email ?? '—'}</div>
                    </td>
                    <td>
                      <div>{item.right?.full_name ?? '—'}</div>
                      <div className="dim mono">{item.right?.phone ?? item.right?.email ?? '—'}</div>
                    </td>
                    <td>
                      <span className="dim" style={{ fontSize: 12 }}>
                        {CANDIDATE_STATUS_LABELS[item.status]}
                      </span>
                    </td>
                    <td className="dim" style={{ fontSize: 11 }}>
                      {item.blocking_keys.map((key) => BLOCKING_KEY_LABELS[key] ?? key).join(' / ')}
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
                <span className="card-title">鉴定证据</span>
                <StatusStamp kind="decision" value={detail.decision} />
                <span className="card-caption" style={{ marginLeft: 'auto' }}>
                  {DECISION_LABELS[detail.decision]} · {formatScore(detail.score)}
                </span>
              </div>
              <RecordDiff left={detail.left} right={detail.right} />
              <div style={{ marginTop: 18 }}>
                <div className="paper-label">加权打分明细</div>
                <ScoreBreakdown candidate={detail} />
              </div>
              <div className="formula" style={{ marginTop: 12 }}>
                总分 = Σ(字段权重 × 相似度) / Σ(可用字段权重)；缺失字段不按 0 分计，而是从分母里剔除。
              </div>

              <div style={{ marginTop: 16 }}>
                <div className="paper-label">落章</div>
                {detail.status !== 'pending' ? (
                  <div className="notice" style={{ marginTop: 8 }}>
                    该候选已由数据管家处理：{CANDIDATE_STATUS_LABELS[detail.status]}
                    {detail.review_note ? ` · ${detail.review_note}` : ''}
                  </div>
                ) : detail.decision !== 'review' ? (
                  <div className="notice" style={{ marginTop: 8 }}>
                    {detail.decision === 'auto'
                      ? '分数已过 auto 阈值，自动并入簇，无需人工落章。'
                      : '分数低于 review 阈值，仅留档不合并。'}
                  </div>
                ) : (
                  <div style={{ marginTop: 8 }}>
                    <label className="field">
                      <span className="field-label">复核意见（写入审计）</span>
                      <textarea
                        rows={2}
                        value={note}
                        onChange={(event) => setNote(event.target.value)}
                        placeholder="例如：姓名/手机一致，地址为搬家后新址"
                      />
                    </label>
                    <div className="btn-row">
                      <button
                        className="btn primary"
                        disabled={!canAct || busy}
                        onClick={() => void review('confirm')}
                      >
                        确认合并
                      </button>
                      <button className="btn" disabled={!canAct || busy} onClick={() => void review('reject')}>
                        拒绝合并
                      </button>
                      {detail.status === 'pending' && detail.decision === 'review' && !canReview ? (
                        <span className="dim" style={{ fontSize: 12 }}>
                          需要 admin / curator 角色
                        </span>
                      ) : null}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="paper-card">
              <EmptyState title="选择左侧一对候选" hint="右侧会展示并置字段、相似度明细与落章按钮。" />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
