import { SOURCE_LABELS } from '../../constants/resolution';
import type { GoldenField } from '../../types/models';
import { formatScore } from '../../utils/formatScore';

interface Props {
  fields: GoldenField[];
}

/** 黄金档案字段级来源与仲裁理由。 */
export const FieldProvenance = ({ fields }: Props) => (
  <div>
    {fields.map((field) => (
      <div key={field.field} style={{ padding: '10px 0', borderBottom: '1px dashed var(--line)' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
          <div className="paper-label">{field.label}</div>
          {field.conflict ? <span className="stamp press">存在冲突</span> : null}
          <div style={{ marginLeft: 'auto', fontSize: 12 }} className="dim">
            可靠性 <span className="num">{formatScore(field.reliability)}</span>
          </div>
        </div>
        <div
          style={{
            fontFamily: 'var(--font-display)',
            fontSize: 19,
            margin: '4px 0 2px',
            overflowWrap: 'anywhere',
          }}
        >
          {field.value ?? '—'}
        </div>
        <div className="dim" style={{ fontSize: 12 }}>
          来源 {field.source_system ? SOURCE_LABELS[field.source_system] ?? field.source_system : '—'}
          {field.source_external_id ? ` · ${field.source_external_id}` : ''}
        </div>
        <div className="formula" style={{ marginTop: 6 }}>
          {field.reason}
        </div>
        {field.alternatives.length > 0 ? (
          <div className="dim" style={{ fontSize: 12, marginTop: 5 }}>
            落选候选：
            {field.alternatives
              .map(
                (alt) =>
                  `${alt.value}（${SOURCE_LABELS[alt.source_system] ?? alt.source_system}，${formatScore(
                    alt.reliability,
                  )}）`,
              )
              .join('；')}
          </div>
        ) : null}
      </div>
    ))}
  </div>
);
