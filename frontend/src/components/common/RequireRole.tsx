import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { tokenStore } from '../../api/client';
import { useAuthStore } from '../../stores/authStore';
import type { Role } from '../../types/models';

interface Props {
  roles: Role[];
  children: ReactNode;
  fallbackPath?: string;
  message?: string;
}

/** 角色白名单：已登录但 user 尚未加载完时先显示加载态，避免直链刷新被踢。 */
export const RequireRole = ({ roles, children, fallbackPath = '/golden', message }: Props) => {
  const user = useAuthStore((state) => state.user);
  if (!tokenStore.get()) return <Navigate to="/login" replace />;
  if (!user) return <div className="loading-line">加载会话…</div>;
  if (!roles.includes(user.role)) {
    return (
      <div className="paper-card">
        <div className="paper-label">权限不足</div>
        <p className="soft" style={{ marginTop: 10 }}>
          {message ?? `当前角色（${user.role}）不能访问该页面。`}
        </p>
        <p className="dim" style={{ fontSize: 13 }}>
          正在跳转到 {fallbackPath}，可继续查看黄金档案。
        </p>
        <Navigate to={fallbackPath} replace />
      </div>
    );
  }
  return <>{children}</>;
};
