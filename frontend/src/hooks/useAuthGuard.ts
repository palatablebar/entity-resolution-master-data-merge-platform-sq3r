import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { tokenStore } from '../api/client';
import { useAuthStore } from '../stores/authStore';

/** 已登录用户直链刷新时，先把 /auth/me 拉回来再渲染页面。 */
export const useAuthGuard = () => {
  const user = useAuthStore((state) => state.user);
  const loadMe = useAuthStore((state) => state.loadMe);
  const navigate = useNavigate();

  useEffect(() => {
    if (!tokenStore.get()) {
      navigate('/login', { replace: true });
      return;
    }
    if (!user) void loadMe();
  }, [user, loadMe, navigate]);

  return useAuthStore((state) => state.user);
};
