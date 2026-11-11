import type { Role } from '../types/models';

export const ROLE_LABELS: Record<Role, string> = {
  admin: '主数据管理员',
  curator: '数据管家',
  marketing: '营销运营（只读）',
};

/** 能力矩阵与后端 src/constants/roles.py 保持一致 */
export const ROLE_PERMISSIONS: Record<Role, string[]> = {
  admin: [
    'records:read',
    'candidates:read',
    'candidates:review',
    'clusters:read',
    'golden:read',
    'golden:export',
    'rules:read',
    'rules:write',
    'runs:read',
    'runs:trigger',
    'audit:read',
  ],
  curator: [
    'records:read',
    'candidates:read',
    'candidates:review',
    'clusters:read',
    'golden:read',
    'golden:export',
    'rules:read',
    'runs:read',
    'runs:trigger',
  ],
  marketing: [
    'records:read',
    'candidates:read',
    'clusters:read',
    'golden:read',
    'golden:export',
    'rules:read',
    'runs:read',
  ],
};

export const can = (role: Role | undefined, action: string): boolean =>
  role ? (ROLE_PERMISSIONS[role] ?? []).includes(action) : false;

export const ROLE_HOME: Record<Role, string> = {
  admin: '/candidates',
  curator: '/candidates',
  marketing: '/golden',
};
