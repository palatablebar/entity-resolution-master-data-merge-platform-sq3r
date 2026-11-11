import type {
  CandidateDecision,
  CandidateStatus,
  ClusterEdgeType,
  ClusterStatus,
  GoldenStatus,
  RunStatus,
} from '../types/models';

/** 共享枚举 2/2（前端一份）：与 backend src/constants/enums.py 对应 */
export const DECISION_LABELS: Record<CandidateDecision, string> = {
  auto: '自动合并',
  review: '待复核',
  reject: '拒绝',
};

export const CANDIDATE_STATUS_LABELS: Record<CandidateStatus, string> = {
  pending: '未处理',
  confirmed: '已确认',
  rejected: '已拒绝',
};

export const CLUSTER_STATUS_LABELS: Record<ClusterStatus, string> = {
  auto_merged: '自动成簇',
  pending_review: '待复核',
  confirmed: '已确认',
  split: '已拆分',
};

export const GOLDEN_STATUS_LABELS: Record<GoldenStatus, string> = {
  active: '生效',
  provisional: '暂定',
  retired: '已退役',
};

export const EDGE_TYPE_LABELS: Record<ClusterEdgeType, string> = {
  auto: '自动边',
  review: '复核边',
  curated: '人工成组',
};

export const RUN_STATUS_LABELS: Record<RunStatus, string> = {
  queued: '排队中',
  running: '运行中',
  succeeded: '已完成',
  failed: '失败',
};

export const FIELD_LABELS: Record<string, string> = {
  name: '姓名',
  phone: '手机',
  email: '邮箱',
  address: '地址',
};

export const BLOCKING_KEY_LABELS: Record<string, string> = {
  phone_suffix: '手机后 4 位',
  name_city: '姓名首字 + 城市',
  email_domain: '邮箱域名',
};

export const SOURCE_LABELS: Record<string, string> = {
  pos: 'POS 收银',
  ecommerce: '电商商城',
  service: '客服工单',
};

export const DECISION_STAMP: Record<CandidateDecision, string> = {
  auto: 'olive',
  review: 'amber',
  reject: '',
};

export const SCORE_BIN_LABELS = ['0-.1', '.1-.2', '.2-.3', '.3-.4', '.4-.5', '.5-.6', '.6-.7', '.7-.8', '.8-.9', '.9-1'];
