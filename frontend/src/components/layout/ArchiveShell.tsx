import { useEffect, type ReactNode } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { ROLE_LABELS } from '../../constants/roles';
import { useAuthStore } from '../../stores/authStore';
import { useRunStore } from '../../stores/runStore';

const NAV = [
  { to: '/candidates', label: '候选复核' },
  { to: '/clusters', label: '实体簇' },
  { to: '/golden', label: '黄金档案' },
  { to: '/rules', label: '规则与阈值' },
  { to: '/runs', label: '运行报告' },
];

/** 档案鉴定室外壳：顶部案卷线 + 导航 + 待复核计数。 */
export const ArchiveShell = ({ children }: { children: ReactNode }) => {
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const navigate = useNavigate();
  const overview = useRunStore((state) => state.overview);
  const refresh = useRunStore((state) => state.refresh);

  useEffect(() => {
    if (!overview) void refresh();
  }, [overview, refresh]);

  const pending = overview?.counts.pending_reviews ?? 0;

  return (
    <div className="archive-shell">
      <header className="topline">
        <div className="brand">
          <span className="brand-name">entresolv</span>
          <span className="brand-sub">会员主数据 · 鉴定室</span>
        </div>
        <nav className="nav">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="topline-right">
          <span>
            待复核 <span className="num" style={{ color: 'var(--vermilion)' }}>{pending}</span>
          </span>
          <span className="dim">|</span>
          <span>{user?.display_name ?? '—'}</span>
          <span className="role-tag">{user ? ROLE_LABELS[user.role] : ''}</span>
          <button
            className="btn ghost"
            onClick={() => {
              logout();
              navigate('/login', { replace: true });
            }}
          >
            退出
          </button>
        </div>
      </header>
      <main className="main">{children}</main>
    </div>
  );
};
