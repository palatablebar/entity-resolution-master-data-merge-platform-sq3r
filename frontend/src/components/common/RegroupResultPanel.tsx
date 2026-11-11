import { StatusStamp } from './StatusStamp';
import { EDGE_TYPE_LABELS } from '../../constants/resolution';
import type { RegroupGroupSnapshot, RegroupResult } from '../../types/models';
import { formatScore } from '../../utils/formatScore';

const GroupLine = ({ group }: { group: RegroupGroupSnapshot }) => (
  <div style={{ padding: '8px 0', borderBottom: '1px dashed var(--line, #ddd)' }}>
    <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
      <StatusStamp kind="cluster" value={group.status} />
      <span className="dim" style={{ fontSize: 11 }}>
        {EDGE_TYPE_LABELS[group.edge_type] ?? group.edge_type}
      </span>
      <span className="dim" style={{ fontSize: 11 }}>
        {group.record_count} 条记录
      </span>
      {group.golden_status ? (
        <span style={{ marginLeft: 'auto', display: 'inline-flex', gap: 6, alignItems: 'center' }}>
          <span className="dim" style={{ fontSize: 11 }}>档案</span>
          <StatusStamp kind="golden" value={group.golden_status} />
        </span>
      ) : (
        <span className="dim" style={{ marginLeft: 'auto', fontSize: 11 }}>无档案</span>
      )}
    </div>
    <div className="mono soft" style={{ fontSize: 12, marginTop: 4 }}>
      {group.member_keys.join(' / ') || '—'}
    </div>
  </div>
);

interface Props {
  regroup: RegroupResult;
}

/** 落章后的重新成组结果：处理前/后分组成员、待定关系与黄金档案状态。 */
export const RegroupResultPanel = ({ regroup }: Props) => (
  <div className="paper-card" style={{ marginTop: 14 }}>
    <div className="card-head">
      <span className="card-title">重新成组结果</span>
      <span className="card-caption" style={{ marginLeft: 'auto' }}>
        作用域 {regroup.scope_record_ids.length} 条记录 · 待定关系 {regroup.pending_edges.length} 条
      </span>
    </div>
    {regroup.idempotent ? (
      <div className="notice" style={{ marginBottom: 12 }}>
        同一判断重复执行：未新增簇或档案，以下为当前成组状态。
      </div>
    ) : null}
    <div className="split" style={{ gap: 14 }}>
      <div>
        <div className="paper-label">处理前分组</div>
        {regroup.before.length === 0 ? (
          <div className="dim" style={{ fontSize: 12, padding: '6px 0' }}>（作用域内此前没有簇）</div>
        ) : (
          regroup.before.map((group) => <GroupLine key={group.cluster_id} group={group} />)
        )}
      </div>
      <div>
        <div className="paper-label">处理后分组</div>
        {regroup.after.length === 0 ? (
          <div className="dim" style={{ fontSize: 12, padding: '6px 0' }}>
            （关系全部落定，不再保留簇）
          </div>
        ) : (
          regroup.after.map((group) => <GroupLine key={group.cluster_id} group={group} />)
        )}
      </div>
    </div>
    {(regroup.split ?? []).length > 0 ? (
      <>
        <div className="paper-label" style={{ marginTop: 12 }}>已拆分留痕（档案同步退役，不下发营销）</div>
        {(regroup.split ?? []).map((group) => (
          <GroupLine key={group.cluster_id} group={group} />
        ))}
      </>
    ) : null}
    <div className="paper-label" style={{ marginTop: 12 }}>待定关系（未决记录保持待定）</div>
    {regroup.pending_edges.length === 0 ? (
      <div className="dim" style={{ fontSize: 12, padding: '6px 0' }}>作用域内没有待复核的候选边。</div>
    ) : (
      <table className="table" style={{ marginTop: 6 }}>
        <thead>
          <tr>
            <th>左侧</th>
            <th>右侧</th>
            <th>分数</th>
            <th>状态</th>
          </tr>
        </thead>
        <tbody>
          {regroup.pending_edges.map((edge) => (
            <tr key={edge.id}>
              <td className="mono" style={{ fontSize: 12 }}>{edge.left_key}</td>
              <td className="mono" style={{ fontSize: 12 }}>{edge.right_key}</td>
              <td className="num">{formatScore(edge.score)}</td>
              <td>
                <StatusStamp kind="candidate" value={edge.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    )}
  </div>
);
