import { FIELD_LABELS } from '../../constants/resolution';
import type { Candidate } from '../../types/models';
import { formatScore } from '../../utils/formatScore';

interface Props {
  candidate: Candidate;
}

const METHOD_LABELS: Record<string, string> = {
  jaro_winkler: 'Jaro-Winkler',
  normalized_exact: '归一化精确',
  token_jaccard: 'Token Jaccard',
};

/** 逐字段相似度与加权贡献，全部由后端算好后端返回，前端只画。 */
export const ScoreBreakdown = ({ candidate }: Props) => {
  const features = Object.values(candidate.features ?? {});
  const order = ['name', 'phone', 'email', 'address'];
  features.sort((a, b) => order.indexOf(a.field) - order.indexOf(b.field));
  return (
    <div>
      <div className="metric-row" style={{ alignItems: 'baseline' }}>
        <div className="metric">
          <div className="metric-label">加权总分</div>
          <div className="metric-value vermilion">{formatScore(candidate.score)}</div>
        </div>
        <div className="metric">
          <div className="metric-label">阈值区间</div>
          <div className="soft" style={{ fontSize: 13 }}>
            auto ≥ {formatScore(candidate.thresholds?.auto ?? 0.92)} · review ≥{' '}
            {formatScore(candidate.thresholds?.review ?? 0.75)}
          </div>
        </div>
        <div className="metric">
          <div className="metric-label">可用权重</div>
          <div className="soft" style={{ fontSize: 13 }}>
            {formatScore(candidate.available_weight)}
          </div>
        </div>
      </div>
      <div style={{ marginTop: 10 }}>
        {features.map((feature) => {
          const similarity = feature.similarity ?? 0;
          return (
            <div className="feature-row" key={feature.field}>
              <div className="soft">{FIELD_LABELS[feature.field] ?? feature.field}</div>
              <div>
                <div className="meter">
                  <div
                    className={`meter-fill ${similarity >= 0.92 ? 'hot' : similarity >= 0.75 ? '' : 'cool'}`}
                    style={{ width: `${Math.max(2, Math.round(similarity * 100))}%` }}
                  />
                </div>
                <div className="dim" style={{ fontSize: 11, marginTop: 2 }}>
                  {METHOD_LABELS[feature.method] ?? feature.method} · 权重 {feature.weight} · 贡献{' '}
                  {feature.contribution}
                </div>
              </div>
              <div className="num" style={{ textAlign: 'right' }}>
                {similarity ? formatScore(similarity) : '缺失'}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
