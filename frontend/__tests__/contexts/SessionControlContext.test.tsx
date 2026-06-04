// @vitest-environment jsdom
import { renderHook, act, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import React from 'react'
import { SessionMapProvider, useSessionMap } from '@/contexts/SessionMapContext'
import {
  SessionControlProvider,
  useSessionControl,
} from '@/contexts/SessionControlContext'
import { DEFAULT_SESSION_CONFIG } from '@/types/session'

const supabaseMocks = vi.hoisted(() => {
  const state = {
    authStateChangeHandler: null as
      | ((event: string, session: { user?: { id: string } } | null) => void)
      | null,
    getUser: vi.fn(),
    onAuthStateChange: vi.fn(),
    unsubscribe: vi.fn(),
    from: vi.fn(),
  }
  state.onAuthStateChange.mockImplementation((handler) => {
    state.authStateChangeHandler = handler
    return {
      data: {
        subscription: {
          unsubscribe: state.unsubscribe,
        },
      },
    }
  })
  return state
})

const sessionServiceMocks = vi.hoisted(() => ({
  listUserSessions: vi.fn(),
}))

vi.mock('@/lib/supabase/client', () => ({
  createClient: vi.fn(() => ({
    auth: {
      getUser: supabaseMocks.getUser,
      onAuthStateChange: supabaseMocks.onAuthStateChange,
    },
    from: supabaseMocks.from,
  })),
}))

vi.mock('@/services/sessions', () => ({
  listUserSessions: sessionServiceMocks.listUserSessions,
}))

// ---------------------------------------------------------------------------
// localStorage mock
// ---------------------------------------------------------------------------
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key]
    }),
    clear: vi.fn(() => {
      store = {}
    }),
    get _store() {
      return store
    },
  }
})()

Object.defineProperty(globalThis, 'localStorage', { value: localStorageMock })

// ---------------------------------------------------------------------------
// fetch mock
// ---------------------------------------------------------------------------
const fetchMock = vi.fn()
Object.defineProperty(globalThis, 'fetch', { value: fetchMock, writable: true })

// ---------------------------------------------------------------------------
// Wrapper that includes both providers
// ---------------------------------------------------------------------------
function wrapper({ children }: { children: React.ReactNode }) {
  return (
    <SessionMapProvider>
      <SessionControlProvider>{children}</SessionControlProvider>
    </SessionMapProvider>
  )
}

describe('SessionControlContext', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorageMock.clear()
    supabaseMocks.authStateChangeHandler = null
    supabaseMocks.getUser.mockResolvedValue({ data: { user: null } })
    sessionServiceMocks.listUserSessions.mockResolvedValue({
      sessions: [],
      count: 0,
    })
    // Default: config fetch returns 404 so we fall back to defaults
    fetchMock.mockResolvedValue({
      ok: false,
      status: 404,
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  // -----------------------------------------------------------------------
  // Initialization
  // -----------------------------------------------------------------------
  describe('initialization', () => {
    it('initializes with null visibleSessionId', () => {
      const { result } = renderHook(() => useSessionControl(), { wrapper })

      expect(result.current.visibleSessionId).toBeNull()
    })

    it('config defaults to DEFAULT_SESSION_CONFIG', () => {
      const { result } = renderHook(() => useSessionControl(), { wrapper })

      expect(result.current.config).toEqual(DEFAULT_SESSION_CONFIG)
    })

    it('sessionRestored becomes true after mount', async () => {
      const { result } = renderHook(() => useSessionControl(), { wrapper })

      await waitFor(() => {
        expect(result.current.sessionRestored).toBe(true)
      })
    })

    it('loads sessions after SIGNED_IN when provider mounted logged out', async () => {
      sessionServiceMocks.listUserSessions.mockResolvedValue({
        sessions: [
          {
            id: 's-1',
            title: 'Recovered chat',
            preview: 'Welcome back',
            created_at: '2026-05-01T10:00:00Z',
            updated_at: '2026-05-01T11:00:00Z',
          },
        ],
        count: 1,
      })

      const { result } = renderHook(
        () => ({
          control: useSessionControl(),
          map: useSessionMap(),
        }),
        { wrapper },
      )

      await waitFor(() => {
        expect(supabaseMocks.onAuthStateChange).toHaveBeenCalled()
      })

      await act(async () => {
        supabaseMocks.authStateChangeHandler?.('SIGNED_IN', {
          user: { id: 'user-123' },
        })
        await Promise.resolve()
      })

      await waitFor(() => {
        expect(sessionServiceMocks.listUserSessions).toHaveBeenCalledTimes(1)
      })
      await waitFor(() => {
        expect(result.current.map.sessions).toEqual([
          {
            id: 's-1',
            title: 'Recovered chat',
            preview: 'Welcome back',
            createdAt: '2026-05-01T10:00:00Z',
            updatedAt: '2026-05-01T11:00:00Z',
          },
        ])
      })
      expect(result.current.control.sessionsLoaded).toBe(true)
    })

    it('clears user-scoped session state on SIGNED_OUT', async () => {
      supabaseMocks.getUser.mockResolvedValue({
        data: { user: { id: 'user-123' } },
      })
      sessionServiceMocks.listUserSessions.mockResolvedValue({
        sessions: [
          {
            id: 's-1',
            title: 'Existing chat',
            created_at: '2026-05-01T10:00:00Z',
            updated_at: '2026-05-01T11:00:00Z',
          },
        ],
        count: 1,
      })

      const { result } = renderHook(
        () => ({
          control: useSessionControl(),
          map: useSessionMap(),
        }),
        { wrapper },
      )

      await waitFor(() => {
        expect(result.current.map.sessions).toHaveLength(1)
      })

      act(() => {
        result.current.control.setVisibleSessionId('s-1')
      })

      await act(async () => {
        supabaseMocks.authStateChangeHandler?.('SIGNED_OUT', null)
        await Promise.resolve()
      })

      await waitFor(() => {
        expect(result.current.map.sessions).toEqual([])
      })
      expect(result.current.control.visibleSessionId).toBeNull()
      expect(result.current.control.sessionsLoaded).toBe(false)
    })
  })

  // -----------------------------------------------------------------------
  // useSessionControl outside provider
  // -----------------------------------------------------------------------
  describe('useSessionControl outside provider', () => {
    it('throws if used outside SessionControlProvider', () => {
      const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
      expect(() => {
        renderHook(() => useSessionControl())
      }).toThrow('useSessionControl must be used within a SessionControlProvider')
      spy.mockRestore()
    })
  })

  // -----------------------------------------------------------------------
  // createNewChat
  // -----------------------------------------------------------------------
  describe('createNewChat', () => {
    it('generates ID matching expected pattern', () => {
      const { result } = renderHook(() => useSessionControl(), { wrapper })

      let newId: string = ''
      act(() => {
        newId = result.current.createNewChat()
      })

      expect(newId).toMatch(/^session-\d+-[a-z0-9]{2,9}$/)
    })

    it('sets the new session as visibleSessionId', () => {
      const { result } = renderHook(() => useSessionControl(), { wrapper })

      let newId: string = ''
      act(() => {
        newId = result.current.createNewChat()
      })

      expect(result.current.visibleSessionId).toBe(newId)
    })

    it('generates unique IDs on subsequent calls', () => {
      const { result } = renderHook(() => useSessionControl(), { wrapper })

      let id1: string = ''
      let id2: string = ''
      act(() => {
        id1 = result.current.createNewChat()
      })
      act(() => {
        id2 = result.current.createNewChat()
      })

      expect(id1).not.toBe(id2)
      expect(result.current.visibleSessionId).toBe(id2)
    })
  })

  // -----------------------------------------------------------------------
  // setVisibleSessionId
  // -----------------------------------------------------------------------
  describe('setVisibleSessionId', () => {
    it('updates visibleSessionId', () => {
      const { result } = renderHook(() => useSessionControl(), { wrapper })

      act(() => {
        result.current.setVisibleSessionId('some-session-id')
      })

      expect(result.current.visibleSessionId).toBe('some-session-id')
    })

    it('can be set back to null', () => {
      const { result } = renderHook(() => useSessionControl(), { wrapper })

      act(() => {
        result.current.setVisibleSessionId('some-session-id')
      })
      act(() => {
        result.current.setVisibleSessionId(null)
      })

      expect(result.current.visibleSessionId).toBeNull()
    })
  })

  // -----------------------------------------------------------------------
  // selectChat
  // -----------------------------------------------------------------------
  describe('selectChat', () => {
    it('sets visibleSessionId to the given session', () => {
      const { result } = renderHook(() => useSessionControl(), { wrapper })

      act(() => {
        result.current.selectChat('target-session')
      })

      expect(result.current.visibleSessionId).toBe('target-session')
    })
  })

  // -----------------------------------------------------------------------
  // localStorage persistence
  // -----------------------------------------------------------------------
  describe('localStorage persistence', () => {
    it('persists visibleSessionId to localStorage on change', async () => {
      const { result } = renderHook(() => useSessionControl(), { wrapper })

      act(() => {
        result.current.setVisibleSessionId('persisted-session')
      })

      await waitFor(() => {
        expect(localStorageMock.setItem).toHaveBeenCalledWith(
          'pikar_current_session_id',
          'persisted-session',
        )
      })
    })

    it('restores visibleSessionId from localStorage on mount', async () => {
      localStorageMock.setItem('pikar_current_session_id', 'restored-session')
      // Clear mock call counts after manual setItem
      localStorageMock.setItem.mockClear()

      const { result } = renderHook(() => useSessionControl(), { wrapper })

      await waitFor(() => {
        expect(result.current.sessionRestored).toBe(true)
      })
      expect(result.current.visibleSessionId).toBe('restored-session')
    })

    it('removes localStorage key when visibleSessionId is set to null', async () => {
      const { result } = renderHook(() => useSessionControl(), { wrapper })

      act(() => {
        result.current.setVisibleSessionId('some-id')
      })
      act(() => {
        result.current.setVisibleSessionId(null)
      })

      await waitFor(() => {
        expect(localStorageMock.removeItem).toHaveBeenCalledWith(
          'pikar_current_session_id',
        )
      })
    })
  })

  // -----------------------------------------------------------------------
  // Config fetch
  // -----------------------------------------------------------------------
  describe('config fetch', () => {
    it('uses default config while remote session config is disabled', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            max_concurrent_streams: 8,
            memory_eviction_minutes: 60,
            max_active_sessions_in_memory: 50,
          }),
      })

      const { result } = renderHook(() => useSessionControl(), { wrapper })

      await waitFor(() => {
        expect(result.current.sessionRestored).toBe(true)
      })
      expect(result.current.config).toEqual(DEFAULT_SESSION_CONFIG)
      expect(fetchMock).not.toHaveBeenCalled()
    })

    it('uses defaults on fetch failure', async () => {
      fetchMock.mockRejectedValueOnce(new Error('Network error'))

      const { result } = renderHook(() => useSessionControl(), { wrapper })

      await waitFor(() => {
        expect(result.current.sessionRestored).toBe(true)
      })
      expect(result.current.config).toEqual(DEFAULT_SESSION_CONFIG)
    })

    it('keeps defaults even when a partial config response mock is configured', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            max_concurrent_streams: 10,
            // other fields omitted
          }),
      })

      const { result } = renderHook(() => useSessionControl(), { wrapper })

      await waitFor(() => {
        expect(result.current.sessionRestored).toBe(true)
      })
      expect(result.current.config).toEqual(DEFAULT_SESSION_CONFIG)
      expect(fetchMock).not.toHaveBeenCalled()
    })
  })

  // -----------------------------------------------------------------------
  // Stubs (Task 7 placeholders)
  // -----------------------------------------------------------------------
  describe('stub methods', () => {
    it('deleteChat resolves without error', async () => {
      const { result } = renderHook(() => useSessionControl(), { wrapper })

      await expect(result.current.deleteChat('any-id')).resolves.toBeUndefined()
    })

    it('clearAllChats resolves without error', async () => {
      const { result } = renderHook(() => useSessionControl(), { wrapper })

      await expect(result.current.clearAllChats()).resolves.toBeUndefined()
    })

    it('refreshSessions resolves without error', async () => {
      const { result } = renderHook(() => useSessionControl(), { wrapper })

      await expect(result.current.refreshSessions()).resolves.toBeUndefined()
    })

    it('updateSessionTitle resolves without error', async () => {
      const { result } = renderHook(() => useSessionControl(), { wrapper })

      await expect(
        result.current.updateSessionTitle('id', 'title'),
      ).resolves.toBeUndefined()
    })

    it('updateSessionPreview resolves without error', async () => {
      const { result } = renderHook(() => useSessionControl(), { wrapper })

      await expect(
        result.current.updateSessionPreview('id', 'preview'),
      ).resolves.toBeUndefined()
    })

    it('addSessionOptimistic does not throw', () => {
      const { result } = renderHook(() => useSessionControl(), { wrapper })

      expect(() => {
        act(() => {
          result.current.addSessionOptimistic({
            id: 'opt-1',
            title: 'Optimistic',
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
          })
        })
      }).not.toThrow()
    })
  })
})
