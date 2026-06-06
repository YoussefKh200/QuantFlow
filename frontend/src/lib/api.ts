/**
 * QuantFlow API client.
 * - Axios with JWT Bearer header injection
 * - Automatic token refresh on 401
 * - Request deduplication for identical in-flight requests
 */
import axios, {
  AxiosError,
  AxiosInstance,
  InternalAxiosRequestConfig,
} from "axios";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ----------------------------------------------------------------
// Token storage (browser only — SSR-safe)
// ----------------------------------------------------------------
const TOKEN_KEY = "qf_access_token";
const REFRESH_KEY = "qf_refresh_token";

export const tokenStorage = {
  getAccess: (): string | null =>
    typeof window !== "undefined" ? localStorage.getItem(TOKEN_KEY) : null,
  getRefresh: (): string | null =>
    typeof window !== "undefined" ? localStorage.getItem(REFRESH_KEY) : null,
  set: (access: string, refresh: string) => {
    localStorage.setItem(TOKEN_KEY, access);
    localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

// ----------------------------------------------------------------
// Axios instance
// ----------------------------------------------------------------
const api: AxiosInstance = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  timeout: 30_000,
  headers: { "Content-Type": "application/json" },
});

// Request interceptor — inject access token
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = tokenStorage.getAccess();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor — handle 401 with token refresh
let _isRefreshing = false;
let _refreshQueue: Array<(token: string) => void> = [];

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      if (_isRefreshing) {
        // Queue request until refresh completes
        return new Promise((resolve) => {
          _refreshQueue.push((token: string) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            resolve(api(originalRequest));
          });
        });
      }

      _isRefreshing = true;
      const refreshToken = tokenStorage.getRefresh();

      if (!refreshToken) {
        tokenStorage.clear();
        window.location.href = "/login";
        return Promise.reject(error);
      }

      try {
        const { data } = await axios.post(`${BASE_URL}/api/v1/auth/refresh`, {
          refresh_token: refreshToken,
        });
        tokenStorage.set(data.access_token, data.refresh_token);
        _refreshQueue.forEach((cb) => cb(data.access_token));
        _refreshQueue = [];
        originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
        return api(originalRequest);
      } catch {
        tokenStorage.clear();
        window.location.href = "/login";
        return Promise.reject(error);
      } finally {
        _isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default api;

// ----------------------------------------------------------------
// Typed API helpers
// ----------------------------------------------------------------
export const authApi = {
  login: (email: string, password: string) =>
    api.post<{ access_token: string; refresh_token: string }>("/auth/login", {
      email, password,
    }),
  me: () => api.get("/auth/me"),
  logout: (refresh_token: string) => api.post("/auth/logout", { refresh_token }),
};

export const optionsApi = {
  chain: (symbol: string) => api.get(`/options/chain/${symbol}`),
  greeks: (symbol: string) => api.get(`/options/greeks/${symbol}`),
  ivSurface: (symbol: string) => api.get(`/options/iv-surface/${symbol}`),
  ivRank: (symbol: string) => api.get(`/options/iv-rank/${symbol}`),
  termStructure: (symbol: string) => api.get(`/options/term-structure/${symbol}`),
  skew: (symbol: string) => api.get(`/options/skew/${symbol}`),
};

export const dealerApi = {
  gex: (symbol: string) => api.get(`/dealer/gex/${symbol}`),
  summary: (symbol: string) => api.get(`/dealer/summary/${symbol}`),
  levels: (symbol: string) => api.get(`/dealer/levels/${symbol}`),
  heatmap: (symbol: string) => api.get(`/dealer/heatmap/${symbol}`),
  history: (symbol: string) => api.get(`/dealer/history/${symbol}`),
};

export const flowApi = {
  scanner: () => api.get("/flow/scanner"),
  unusual: () => api.get("/flow/unusual"),
  sentiment: (symbol: string) => api.get(`/flow/sentiment/${symbol}`),
};

export const volatilityApi = {
  regime: (symbol: string) => api.get(`/volatility/regime/${symbol}`),
  metrics: (symbol: string) => api.get(`/volatility/metrics/${symbol}`),
  history: (symbol: string) => api.get(`/volatility/history/${symbol}`),
};

export const earningsApi = {
  calendar: () => api.get("/earnings/calendar"),
  history: (symbol: string) => api.get(`/earnings/history/${symbol}`),
  pead: (symbol: string) => api.get(`/earnings/pead/${symbol}`),
  signals: () => api.get("/earnings/signals"),
};

export const alertsApi = {
  list: () => api.get("/alerts"),
  create: (data: object) => api.post("/alerts", data),
  delete: (id: string) => api.delete(`/alerts/${id}`),
};
