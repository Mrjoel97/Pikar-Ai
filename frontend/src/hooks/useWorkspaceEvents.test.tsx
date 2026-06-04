// @vitest-environment jsdom

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import type { FetchEventSourceInit } from '@microsoft/fetch-event-source';
import type { WorkspaceEvent } from '@/types/workspace-events';

const fetchEventSourceMock = vi.hoisted(() => vi.fn());
const getAccessTokenMock = vi.hoisted(() => vi.fn());

vi.mock('@microsoft/fetch-event-source', () => ({
    fetchEventSource: fetchEventSourceMock,
}));

vi.mock('@/lib/supabase/client', () => ({
    getAccessToken: getAccessTokenMock,
}));

vi.mock('@/services/api', () => ({
    API_BASE_URL: 'https://api.example.com',
}));

import { useWorkspaceEvents } from './useWorkspaceEvents';

describe('useWorkspaceEvents', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        getAccessTokenMock.mockResolvedValue('jwt-123');
        fetchEventSourceMock.mockResolvedValue(undefined);
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('opens a fetch SSE stream with the current access token', async () => {
        renderHook(() => useWorkspaceEvents());

        await waitFor(() => expect(fetchEventSourceMock).toHaveBeenCalledTimes(1));
        const [url, init] = fetchEventSourceMock.mock.calls[0] as [
            string,
            FetchEventSourceInit,
        ];
        expect(url).toBe('https://api.example.com/workspace/events');
        expect(init.headers).toMatchObject({
            Accept: 'text/event-stream',
            Authorization: 'Bearer jwt-123',
        });
    });

    it('appends incoming events in order', async () => {
        const a: WorkspaceEvent = {
            kind: 'progress',
            agent_id: 'FIN',
            contract_id: null,
            item: 'step',
            status: 'started',
        };
        const b: WorkspaceEvent = {
            kind: 'artifact',
            agent_id: 'FIN',
            contract_id: null,
            artifact_kind: 'report',
            ref: 'vault://1',
            summary: 's',
            preview_url: null,
        };
        fetchEventSourceMock.mockImplementation(async (_url, init: FetchEventSourceInit) => {
            act(() => {
                init.onmessage?.({ data: JSON.stringify(a), event: '', id: '', retry: undefined });
                init.onmessage?.({ data: JSON.stringify(b), event: '', id: '', retry: undefined });
            });
        });

        const { result } = renderHook(() => useWorkspaceEvents());

        await waitFor(() => expect(result.current).toHaveLength(2));
        expect(result.current[0]).toEqual(a);
        expect(result.current[1]).toEqual(b);
    });

    it('aborts the stream on unmount', async () => {
        let signal: AbortSignal | undefined;
        fetchEventSourceMock.mockImplementation(async (_url, init: FetchEventSourceInit) => {
            signal = init.signal;
        });

        const { unmount } = renderHook(() => useWorkspaceEvents());

        await waitFor(() => expect(signal).toBeDefined());
        expect(signal?.aborted).toBe(false);
        unmount();
        expect(signal?.aborted).toBe(true);
    });

    it('ignores malformed payloads instead of crashing', async () => {
        fetchEventSourceMock.mockImplementation(async (_url, init: FetchEventSourceInit) => {
            act(() => {
                init.onmessage?.({ data: '{not-json', event: '', id: '', retry: undefined });
            });
        });

        const spy = vi.spyOn(console, 'warn').mockImplementation(() => {});
        const { result } = renderHook(() => useWorkspaceEvents());

        await waitFor(() => expect(spy).toHaveBeenCalled());
        expect(result.current).toEqual([]);
    });

    it('drops events with an unknown kind', async () => {
        fetchEventSourceMock.mockImplementation(async (_url, init: FetchEventSourceInit) => {
            act(() => {
                init.onmessage?.({
                    data: JSON.stringify({ kind: 'mystery', agent_id: 'X' }),
                    event: '',
                    id: '',
                    retry: undefined,
                });
            });
        });

        const spy = vi.spyOn(console, 'warn').mockImplementation(() => {});
        const { result } = renderHook(() => useWorkspaceEvents());

        await waitFor(() => expect(spy).toHaveBeenCalled());
        expect(result.current).toEqual([]);
    });
});
