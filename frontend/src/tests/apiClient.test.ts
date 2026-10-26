import { apiClient } from '../lib/apiClient';
import { useAuthStore } from '../state/authStore';

// Mock fetch globally
globalThis.fetch = jest.fn();

describe('apiClient refresh logic', () => {
  beforeEach(() => {
    (globalThis.fetch as jest.Mock).mockClear();
    useAuthStore.setState({ accessToken: 'old-token', user: { id: '1', email: 'test@example.com', organizations: [] } });
  });

  it('handles 401 and refreshes token exactly once', async () => {
    // 1st fetch: 401
    // 2nd fetch (refresh): 200 with new token
    // 3rd fetch (retry): 200

    (globalThis.fetch as jest.Mock)
      .mockResolvedValueOnce({
        status: 401,
        ok: false,
      })
      .mockResolvedValueOnce({
        status: 200,
        ok: true,
        json: async () => ({ access_token: 'new-token' }),
      })
      .mockResolvedValueOnce({
        status: 200,
        ok: true,
        json: async () => ({ data: 'success' }),
      });

    const result = await apiClient('/test-endpoint');

    expect(globalThis.fetch).toHaveBeenCalledTimes(3);
    expect(globalThis.fetch).toHaveBeenNthCalledWith(1, '/api/v1/test-endpoint', expect.objectContaining({
      headers: expect.any(Headers)
    }));
    
    // Check if refresh was called
    expect(globalThis.fetch).toHaveBeenNthCalledWith(2, '/api/v1/auth/refresh', expect.objectContaining({
      method: 'POST'
    }));

    // Check if new token is saved
    expect(useAuthStore.getState().accessToken).toBe('new-token');
    
    expect(result).toEqual({ data: 'success' });
  });
});
