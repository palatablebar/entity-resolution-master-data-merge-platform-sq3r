import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { RuleUpdate } from '../api/rules';
import { runApi } from '../api/runs';
import { EmptyState } from '../components/common/EmptyState';
import { useAuthGuard } from '../hooks/useAuthGuard';
import { useAuthStore } from '../stores/authStore';
import { useRuleStore } from '../stores/ruleStore';
import { useRunStore } from '../stores/runStore';
import type { MergeRule } from '../types/models';
import { toHumanMessage } from '../utils/errorMessage';
import { formatDateTime } from '../utils/formatScore';

const WEIGHT_FIELDS = [
  { key: 'name', label: '姓名', method: 'Jaro-Winkler（自实现）' },
  { key: 'phone', label: '手机', method: '归一化精确匹配' },
  { key: 'email', label: '邮箱', method: '归一化精确匹配' },
  { key: 'address', label: '地址', method: '分词 Token Jaccard' },
];

const SOURCE_FIELDS = [
  { key: 'pos', label: 'POS 收银' },
  { key: 'ecommerce', label: '电商商城' },
  { key: 'service', label: '客服工单' },
];

export const RulesPage = () => {
  useAuthGuard();
  const navigate = useNavigate();
  const canWrite = useAuthStore((state) => state.can)('rules:write');
  const canTrigger = useAuthStore((state) => state.can)('runs:trigger');
  const refreshOverview = useRunStore((state) => state.refresh);

  const rules = useRuleStore((state) => state.rules);
  const loadRules = useRuleStore((state) => state.load);
  const saveRule = useRuleStore((state) => state.save);
  const storeError = useRuleStore((state) => state.error);
  const [ruleId, setRuleId] = useState<string | null>(null);
  const [weights, setWeights] = useState<Record<string, number>>({});
  const [reliability, setReliability] = useState<Record<string, number>>({});
  const [autoThreshold, setAutoThreshold] = useState(0.92);
  const [reviewThreshold, setReviewThreshold] = useState(0.75);
  const [busy, setBusy] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = async () => {
    const items = await loadRules();
    const preferred = items.find((item) => item.is_active) ?? items[0];
    if (preferred) applyRule(preferred, false);
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const applyRule = (rule: MergeRule, clearMessage = true) => {
    setRuleId(rule.id);
    setWeights({ ...rule.field_weights });
    setReliability({ ...rule.source_reliability });
    setAutoThreshold(rule.auto_threshold);
    setReviewThreshold(rule.review_threshold);
    if (clearMessage) setMessage(null);
  };

  const current = useMemo(() => rules.find((item) => item.id === ruleId) ?? null, [rules, ruleId]);
  const weightSum = useMemo(
    () => Object.values(weights).reduce((acc, value) => acc + (Number(value) || 0), 0),
    [weights],
  );

  const save = async () => {
    if (!ruleId) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    const payload: RuleUpdate = {
      field_weights: weights,
      source_reliability: reliability,
      auto_threshold: autoThreshold,
      review_threshold: reviewThreshold,
    };
    try {
      const updated = await saveRule(ruleId, payload);
      if (!updated) {
        setError('规则保存失败，请检查阈值关系与权重范围。');
        return;
      }
      setMessage(`规则已保存，版本 v${updated.version}。新版本只影响之后发起的运行。`);
      await load();
    } catch (err) {
      setError(toHumanMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const trigger = async () => {
    setTriggering(true);
    setError(null);
    setMessage(null);
    try {
      const run = await runApi.create({
        rule_id: ruleId ?? undefined,
        run_label: `规则调整后重跑 · ${new Date().toLocaleTimeString('zh-CN', { hour12: false })}`,
      });
      await refreshOverview();
      navigate(`/runs?run=${run.id}`);
    } catch (err) {
      setError(toHumanMessage(err));
    } finally {
      setTriggering(false);
    }
  };

  return (
    <div className="enter">
      <div className="page-head">
        <div>
          <div className="page-kicker">案卷 04 · 规则与阈值</div>
          <h1 className="page-title">鉴定尺度</h1>
        </div>
        <div className="page-note">
          权重决定字段话语权，阈值决定 auto / review / reject 的边界。保存后不会改动历史运行：
          每次运行的参数都会快照进运行报告。
        </div>
        <div className="head-actions">
          <label className="field" style={{ marginBottom: 0, minWidth: 260 }}>
            <span className="field-label">规则集</span>
            <select
              value={ruleId ?? ''}
              onChange={(event) => {
                const rule = rules.find((item) => item.id === event.target.value);
                if (rule) applyRule(rule);
              }}
            >
              {rules.map((rule) => (
                <option key={rule.id} value={rule.id}>
                  {rule.name}
                  {rule.is_active ? '（生效中）' : ''}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {(error ?? storeError) ? (
        <div className="notice error" style={{ marginBottom: 14 }}>{error ?? storeError}</div>
      ) : null}
      {message ? <div className="notice" style={{ marginBottom: 14 }}>{message}</div> : null}
      {!canWrite ? (
        <div className="notice" style={{ marginBottom: 14 }}>
          当前角色（admin 之外）只能查看规则；修改权重与阈值需要主数据管理员。
        </div>
      ) : null}

      {current ? (
        <div className="split">
          <div className="paper-card">
            <div className="card-head">
              <span className="card-title">字段权重</span>
              <span className="card-caption">合计 {weightSum.toFixed(2)}（不强制为 1，打分时按可用权重归一分母）</span>
            </div>
            {WEIGHT_FIELDS.map((field) => (
              <div key={field.key} className="field">
                <span className="field-label">
                  {field.label} · {field.method}
                </span>
                <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max="1"
                    value={weights[field.key] ?? 0}
                    disabled={!canWrite}
                    onChange={(event) =>
                      setWeights((state) => ({ ...state, [field.key]: Number(event.target.value) }))
                    }
                    style={{ width: 96 }}
                  />
                  <div className="meter" style={{ flex: 1 }}>
                    <div
                      className="meter-fill"
                      style={{ width: `${Math.min(100, (weights[field.key] ?? 0) * 200)}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}

            <div className="paper-label" style={{ marginTop: 18 }}>来源可靠性（golden record 仲裁权重）</div>
            {SOURCE_FIELDS.map((source) => (
              <div key={source.key} className="field">
                <span className="field-label">{source.label}</span>
                <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max="1"
                    value={reliability[source.key] ?? 0}
                    disabled={!canWrite}
                    onChange={(event) =>
                      setReliability((state) => ({ ...state, [source.key]: Number(event.target.value) }))
                    }
                    style={{ width: 96 }}
                  />
                  <div className="meter" style={{ flex: 1 }}>
                    <div
                      className="meter-fill cool"
                      style={{ width: `${Math.min(100, (reliability[source.key] ?? 0) * 100)}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}

            <div className="btn-row" style={{ marginTop: 16 }}>
              <button className="btn primary" disabled={!canWrite || busy} onClick={() => void save()}>
                {busy ? '保存中…' : '保存并升版'}
              </button>
              <button className="btn" disabled={!canTrigger || triggering} onClick={() => void trigger()}>
                {triggering ? '投递中…' : '按当前规则发起解析'}
              </button>
            </div>
          </div>

          <div>
            <div className="paper-card">
              <div className="card-head">
                <span className="card-title">阈值</span>
                <span className="card-caption">当前 v{current.version} · 更新于 {formatDateTime(current.updated_at)}</span>
              </div>
              <div className="field-row">
                <label className="field">
                  <span className="field-label">auto ≥ 自动合并</span>
                  <input
                    type="number"
                    step="0.01"
                    min="0.5"
                    max="1"
                    value={autoThreshold}
                    disabled={!canWrite}
                    onChange={(event) => setAutoThreshold(Number(event.target.value))}
                  />
                </label>
                <label className="field">
                  <span className="field-label">review ≥ 待复核</span>
                  <input
                    type="number"
                    step="0.01"
                    min="0.3"
                    max="0.99"
                    value={reviewThreshold}
                    disabled={!canWrite}
                    onChange={(event) => setReviewThreshold(Number(event.target.value))}
                  />
                </label>
              </div>
              <div className="formula">
                auto：score ≥ {autoThreshold.toFixed(2)} → 直接并簇
                <br />
                review：{reviewThreshold.toFixed(2)} ≤ score &lt; {autoThreshold.toFixed(2)} → 数据管家落章
                <br />
                reject：score &lt; {reviewThreshold.toFixed(2)} → 仅留档
              </div>
            </div>

            <div className="paper-card tint">
              <div className="card-head">
                <span className="card-title">规范化口径</span>
              </div>
              <table className="table">
                <tbody>
                  <tr>
                    <td className="dim">手机</td>
                    <td>去分隔符 / 国家码，保留最后 11 位；blocking 取后 4 位</td>
                  </tr>
                  <tr>
                    <td className="dim">邮箱</td>
                    <td>小写去空白；blocking 取域名</td>
                  </tr>
                  <tr>
                    <td className="dim">姓名</td>
                    <td>全角转半角、去标点空格；blocking 取首字 + 城市</td>
                  </tr>
                  <tr>
                    <td className="dim">地址</td>
                    <td>去标点，中文按 2-gram + 拉丁词分词，算 Token Jaccard</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : (
        <div className="paper-card">
          <EmptyState title="还没有规则集" hint="后端首次启动会创建默认规则；如为空请跑一次 seed。" />
        </div>
      )}
    </div>
  );
};
