'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { useEffect, useState } from 'react';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import type { WorkspaceEvent } from '@/types/workspace-events';
import { getAccessToken } from '@/lib/supabase/client';
import { API_BASE_URL } from '@/services/api';

const ENDPOINT = `${API_BASE_URL.replace(/\/+$/, '')}/workspace/events`;
const RECONNECT_DELAY_MS = 5000;

/**
 * Subscribe to the per-user workspace SSE channel and accumulate events.
 *
 * Uses fetch-based SSE instead of native `EventSource` so the browser can send
 * the user's Bearer token. Malformed payloads are logged and skipped — a bad
 * frame must never crash the canvas.
 *
 * Cleanup: the underlying fetch is aborted when the consumer unmounts so we
 * never leak open connections across route transitions.
 */
export function useWorkspaceEvents(): WorkspaceEvent[] {
    const [events, setEvents] = useState<WorkspaceEvent[]>([]);

    useEffect(() => {
        const controller = new AbortController();
        let cancelled = false;
        let retryTimer: ReturnType<typeof setTimeout> | null = null;

        const waitForRetry = () =>
            new Promise<void>((resolve) => {
                retryTimer = setTimeout(resolve, RECONNECT_DELAY_MS);
            });

        const handleMessage = (data: string) => {
            try {
                const parsed = JSON.parse(data) as WorkspaceEvent;
                if (
                    parsed
                    && (parsed.kind === 'progress' || parsed.kind === 'artifact')
                ) {
                    setEvents((prev) => [...prev, parsed]);
                } else {
                    console.warn(
                        '[useWorkspaceEvents] dropping event with unknown kind',
                        parsed,
                    );
                }
            } catch (err) {
                console.warn(
                    '[useWorkspaceEvents] dropping malformed payload',
                    err,
                );
            }
        };

        void (async () => {
            while (!cancelled) {
                const token = await getAccessToken().catch(() => null);
                if (!token) {
                    await waitForRetry();
                    continue;
                }

                try {
                    await fetchEventSource(ENDPOINT, {
                        signal: controller.signal,
                        openWhenHidden: true,
                        headers: {
                            Accept: 'text/event-stream',
                            Authorization: `Bearer ${token}`,
                        },
                        async onopen(response) {
                            if (response.status === 401 || response.status === 403) {
                                throw new Error(`workspace events auth rejected: ${response.status}`);
                            }
                            if (!response.ok) {
                                throw new Error(`workspace events returned ${response.status}`);
                            }
                        },
                        onmessage(message) {
                            handleMessage(message.data);
                        },
                        onerror(error) {
                            throw error;
                        },
                    });
                } catch (err) {
                    if (cancelled || controller.signal.aborted) {
                        break;
                    }
                    if (
                        err instanceof Error
                        && !err.message.startsWith('workspace events auth rejected')
                    ) {
                        console.warn('[useWorkspaceEvents] SSE reconnecting after error', err);
                    }
                }

                if (!cancelled) {
                    await waitForRetry();
                }
            }
        })();

        return () => {
            cancelled = true;
            if (retryTimer) {
                clearTimeout(retryTimer);
            }
            controller.abort();
        };
    }, []);

    return events;
}
