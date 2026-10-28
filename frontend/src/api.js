const ACCESS_KEY = "rekomme_access_token";
const REFRESH_KEY = "rekomme_refresh_token";
const USER_KEY = "rekomme_username";

export const authStore = {
  access: () => localStorage.getItem(ACCESS_KEY),
  refresh: () => localStorage.getItem(REFRESH_KEY),
  username: () => localStorage.getItem(USER_KEY) || "Shopper",
  save(tokens, username) {
    localStorage.setItem(ACCESS_KEY, tokens.access_token);
    localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
    if (username) localStorage.setItem(USER_KEY, username);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
  }
};

async function parseResponse(response) {
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const detail = typeof payload === "object" ? payload.detail : payload;
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return payload;
}

async function refreshAccessToken() {
  const refreshToken = authStore.refresh();
  if (!refreshToken) return false;
  try {
    const response = await fetch("/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken })
    });
    const tokens = await parseResponse(response);
    authStore.save(tokens, authStore.username());
    return true;
  } catch {
    authStore.clear();
    return false;
  }
}

export async function apiFetch(path, options = {}, retry = true) {
  const headers = new Headers(options.headers || {});
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const token = authStore.access();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(path, { ...options, headers });
  if (response.status === 401 && retry && (await refreshAccessToken())) {
    return apiFetch(path, options, false);
  }
  return parseResponse(response);
}

export const api = {
  login: (username, password) =>
    apiFetch("/auth/token", {
      method: "POST",
      body: JSON.stringify({ username, password })
    }),
  register: (data) =>
    apiFetch("/users/", { method: "POST", body: JSON.stringify(data) }),
  categories: () => apiFetch("/choices/categories"),
  sessions: () => apiFetch("/search/chat-sessions"),
  messages: (sessionId) => apiFetch(`/search/messages/${sessionId}`),
  initialSearch: (payload) =>
    apiFetch("/search/initial", { method: "POST", body: JSON.stringify(payload) }),
  followUp: (payload) =>
    apiFetch("/search/followup", { method: "POST", body: JSON.stringify(payload) }),
  listings: (query) =>
    apiFetch("/search/product-listings", {
      method: "POST",
      body: JSON.stringify({ query })
    })
};
