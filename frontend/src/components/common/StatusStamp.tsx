import type { ClusterStatus, CandidateDecision, CandidateStatus, GoldenStatus, RunStatus } from '../../types/models';
import {
  CANDIDATE_STATUS_LABELS,
  CLUSTER_STATUS_LABELS,
  DECISION_LABELS,
  DECISION_STAMP,
  GOLDEN_STATUS_LABELS,
  RUN_STATUS_LABELS,
} from '../../constants/resolution';

type Kind = 'decision' | 'candidate' | 'cluster' | 'golden' | 'run';

const LABELS: Record<Kind, Record<string, string>> = {
  decision: DECISION_LABELS as Record<string, string>,
  candidate: CANDIDATE_STATUS_LABELS as Record<string, string>,
  cluster: CLUSTER_STATUS_LABELS as Record<string, string>,
  golden: GOLDEN_STATUS_LABELS as Record<string, string>,
  run: RUN_STATUS_LABELS as Record<string, string>,
};

const TONE: Record<string, string> = {
  auto: 'olive',
  auto_merged: 'olive',
  active: 'olive',
  succeeded: 'olive',
  confirmed: 'olive',
  review: 'amber',
  pending_review: 'amber',
  provisional: 'amber',
  running: 'amber',
  queued: 'neutral',
  pending: 'neutral',
  split: 'neutral',
  retired: 'neutral',
  reject: '',
  rejected: '',
  failed: '',
};

interface Props {
  kind: Kind;
  value: CandidateDecision | CandidateStatus | ClusterStatus | GoldenStatus | RunStatus | string;
  press?: boolean;
  round?: boolean;
}

export const StatusStamp = ({ kind, value, press = false, round = false }: Props) => {
  const label = LABELS[kind][value] ?? value;
  const tone = TONE[value] ?? '';
  return (
    <span className={`stamp ${tone} ${press ? 'press' : ''} ${round ? 'round' : ''}`}>{label}</span>
  );
};
