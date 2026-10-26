import { useAuthStore } from '../state/authStore';

const BASE_URL = '/api/v1';

export async function apiClient(endpoint: string, options: RequestInit = {}) {
  const { accessToken, clearAuth } = useAuthStore.getState();

  const headers = new Headers(options.headers);
  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`);
  }
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  // Prevent aggressive browser caching of API responses
  if (!headers.has('Cache-Control')) {
    headers.set('Cache-Control', 'no-store, no-cache, must-revalidate, proxy-revalidate');
    headers.set('Pragma', 'no-cache');
    headers.set('Expires', '0');
  }

  const config: RequestInit = {
    ...options,
    headers,
  };

  let response = await fetch(`${BASE_URL}${endpoint}`, config);

  if (response.status === 401) {
    // Attempt to refresh
    try {
      const refreshResponse = await fetch(`${BASE_URL}/auth/refresh`, {
        method: 'POST',
      });

      if (refreshResponse.ok) {
        const data = await refreshResponse.json();
        const newAccessToken = data.access_token || data.accessToken;
        
        const currentStore = useAuthStore.getState();
        if (currentStore.user && newAccessToken) {
          currentStore.setAuth(newAccessToken, currentStore.user);
        }

        // Retry the original request
        headers.set('Authorization', `Bearer ${newAccessToken}`);
        response = await fetch(`${BASE_URL}${endpoint}`, {
          ...options,
          headers,
        });
      } else {
        clearAuth();
      }
    } catch (e) {
      clearAuth();
    }
  }

  if (!response.ok) {
    // If it's still not ok, don't throw generically if they want to handle it, but wait
    // We can just return the response or throw.
    // The instructions say "handles exactly one 401->refresh->retry loop". 
    // We will throw error for simplicity, or return response for them to parse.
  }

  return response;
}
