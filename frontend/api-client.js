/*
 * Highlight Studio — API client (optional integration layer)
 *
 * デフォルトでは何もしない。実際のバックエンド(highlight-studio-backend-skeleton)
 * に接続する場合だけ、各HTMLの <head> より前などで以下のように設定する:
 *
 *   <script>window.HS_API_BASE = 'https://api.example.com';</script>
 *   <script src="./api-client.js"></script>
 *
 * window.HS_API_BASE が未設定の間は HSApi.enabled が false になるので、
 * 各ページ側は「if (window.HSApi && HSApi.enabled) { ...API呼び出し... } else { ...従来のlocalStorageモック... }」
 * という形で分岐させ、バックエンド未接続の状態でもデモが今まで通り動く。
 */
(function () {
  const API_BASE = window.HS_API_BASE || '';

  async function request(path, { method = 'GET', body, auth = false } = {}) {
    const headers = { 'Content-Type': 'application/json' };
    if (auth) {
      const token = localStorage.getItem('hs_accessToken');
      if (token) headers['Authorization'] = `Bearer ${token}`;
    }
    const res = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
    let data = null;
    try { data = await res.json(); } catch (e) { /* 空レスポンス等は無視 */ }
    if (!res.ok) {
      const message = (data && data.error) || `リクエストに失敗しました(${res.status})`;
      throw new Error(message);
    }
    return data;
  }

  window.HSApi = {
    enabled: Boolean(API_BASE),

    signup: (email, password) =>
      request('/api/auth/signup', { method: 'POST', body: { email, password } }),

    login: async (email, password) => {
      const data = await request('/api/auth/login', { method: 'POST', body: { email, password } });
      if (data && data.accessToken) localStorage.setItem('hs_accessToken', data.accessToken);
      return data;
    },

    verifyEmail: (token) =>
      request('/api/auth/verify-email', { method: 'POST', body: { token } }),

    me: () => request('/api/auth/me', { auth: true }),

    updateProfile: (fields) =>
      request('/api/auth/me', { method: 'PATCH', body: fields, auth: true }),

    requestPasswordReset: (email) =>
      request('/api/auth/request-password-reset', { method: 'POST', body: { email } }),

    resetPassword: (token, password) =>
      request('/api/auth/reset-password', { method: 'POST', body: { token, password } }),

    submitContact: (fields) =>
      request('/api/contact', { method: 'POST', body: fields }),

    logout: () => localStorage.removeItem('hs_accessToken'),
  };
})();
