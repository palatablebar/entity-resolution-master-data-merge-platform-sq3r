import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROLE_HOME } from '../constants/roles';
import { useAuthStore } from '../stores/authStore';
import { toHumanMessage } from '../utils/errorMessage';

const ACCOUNTS = [
  { email: 'admin@master.local', note: '全部权限 · 改规则 / 发起解析' },
  { email: 'curator@master.local', note: '复核候选 / 发起解析' },
  { email: 'marketing@master.local', note: '只读 · 黄金档案与导出' },
];

export const LoginPage = () => {
  const login = useAuthStore((state) => state.login);
  const navigate = useNavigate();
  const [email, setEmail] = useState('curator@master.local');
  const [password, setPassword] = useState('Demo@2026');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const user = await login(email, password);
      navigate(ROLE_HOME[user.role] ?? '/candidates', { replace: true });
    } catch (err) {
      setError(toHumanMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="login-page">
      <aside className="login-aside">
        <div className="brand">
          <span className="brand-name">entresolv</span>
          <span className="brand-sub">实体解析与主数据合并台</span>
        </div>
        <div className="seal">康和会员档案</div>
        <div className="login-lede">
          一个人三条记录，该信哪一条？把判断依据留在纸面上。
        </div>
        <p className="soft" style={{ maxWidth: '46ch' }}>
          区域连锁药房「康和」的会员散落在 POS、电商、客服三套系统里，重复率 23%。
          这里用三路 blocking 键捞出可疑对，按姓名 Jaro-Winkler、手机/邮箱归一化精确、
          地址 Token Jaccard 加权打分，再并查集成簇、按来源可靠性仲裁出黄金档案。
          复核确认与规则改动都会留下审计记录。
        </p>
        <ul className="login-points">
          <li>120 条来源记录 · 18 组跨系统重复 · 4 组同名不同人</li>
          <li>候选对并置比对：字段级相似度、权重与贡献逐项可查</li>
          <li>golden record 字段级来源引用：POS / 电商 / 客服谁更可信</li>
          <li>改阈值重跑，自动簇数量随之变化，历史运行留档</li>
        </ul>
        <div className="dim" style={{ fontSize: 12, marginTop: 'auto' }}>
          《主数据治理组 · 日常案卷》 第 2026-11 卷
        </div>
      </aside>

      <section className="login-main">
        <div className="page-kicker">出示证件</div>
        <h1 className="page-title" style={{ margin: '4px 0 18px' }}>
          登录鉴定室
        </h1>
        <form onSubmit={submit}>
          <label className="field">
            <span className="field-label">邮箱</span>
            <input
              type="email"
              value={email}
              autoComplete="username"
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          <label className="field">
            <span className="field-label">密码</span>
            <input
              type="password"
              value={password}
              autoComplete="current-password"
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          {error ? <div className="notice error" style={{ marginBottom: 12 }}>{error}</div> : null}
          <button className="btn primary" type="submit" disabled={submitting} style={{ width: '100%' }}>
            {submitting ? '核对中…' : '进入鉴定室'}
          </button>
        </form>

        <div style={{ marginTop: 26 }}>
          <div className="paper-label">演示账号（密码 Demo@2026）</div>
          <div style={{ marginTop: 6 }}>
            {ACCOUNTS.map((account) => (
              <button
                key={account.email}
                type="button"
                className="account-pick"
                onClick={() => {
                  setEmail(account.email);
                  setPassword('Demo@2026');
                }}
              >
                <span className="mono">{account.email}</span>
                <span className="dim">{account.note}</span>
              </button>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
};
