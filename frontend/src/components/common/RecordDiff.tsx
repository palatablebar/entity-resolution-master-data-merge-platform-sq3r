import { FIELD_LABELS } from '../../constants/resolution';
import type { SourceRecord } from '../../types/models';

const ROWS: Array<{ field: string; normalized: keyof SourceRecord; raw: keyof SourceRecord }> = [
  { field: 'name', normalized: 'normalized_name', raw: 'full_name' },
  { field: 'phone', normalized: 'normalized_phone', raw: 'phone' },
  { field: 'email', normalized: 'normalized_email', raw: 'email' },
  { field: 'address', normalized: 'normalized_address', raw: 'address' },
];

interface Props {
  left?: SourceRecord;
  right?: SourceRecord;
}

/** 左右并置鉴定：按规范化值判定一致/不一致，展示原始值。 */
export const RecordDiff = ({ left, right }: Props) => {
  if (!left || !right) {
    return <div className="loading-line">等待两侧记录…</div>;
  }
  return (
    <div>
      <div className="diff-grid" style={{ borderTop: '1px solid var(--line-strong)' }}>
        <div className="diff-field">字段</div>
        <div className="diff-field">
          {left.source_label}
          <span className="diff-source">{left.external_id}</span>
        </div>
        <div className="diff-field">
          {right.source_label}
          <span className="diff-source">{right.external_id}</span>
        </div>
      </div>
      <div className="diff-grid">
        {ROWS.map((row) => {
          const leftNormalized = left[row.normalized] as string | null;
          const rightNormalized = right[row.normalized] as string | null;
          const leftRaw = left[row.raw] as string | null;
          const rightRaw = right[row.raw] as string | null;
          const changed = Boolean(leftNormalized) && Boolean(rightNormalized) && leftNormalized !== rightNormalized;
          return (
            <FragmentRow
              key={row.field}
              field={FIELD_LABELS[row.field] ?? row.field}
              leftValue={leftRaw}
              rightValue={rightRaw}
              changed={changed}
            />
          );
        })}
      </div>
    </div>
  );
};

const FragmentRow = ({
  field,
  leftValue,
  rightValue,
  changed,
}: {
  field: string;
  leftValue: string | null;
  rightValue: string | null;
  changed: boolean;
}) => (
  <>
    <div className="diff-field">{field}</div>
    <div className={changed ? 'diff-changed' : ''}>
      {leftValue ?? <span className="diff-missing">缺失</span>}
    </div>
    <div className={changed ? 'diff-changed' : ''}>
      {rightValue ?? <span className="diff-missing">缺失</span>}
    </div>
  </>
);
