import { ApiError } from '../types/api';

export const toHumanMessage = (error: unknown): string => {
  if (error instanceof ApiError) {
    if (error.status === 403) return '当前角色无权执行该操作（403）。';
    if (error.status === 401) return '登录状态失效，请重新登录。';
    if (error.status === 429) return '请求过于频繁，请稍后再试。';
    return error.payload.message || error.message;
  }
  if (error instanceof Error) return error.message;
  return '未知错误';
};
