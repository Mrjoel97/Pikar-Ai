// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Proxy for the per-user workspace SSE channel.
 *
 * The browser hook (`useWorkspaceEvents`) opens a fetch-based SSE stream
 * against the Next.js origin with an Authorization header. We still keep the
 * SSR cookie fallback here so older clients and cookie-backed refreshes can
 * authenticate without native EventSource header support.
 */

import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { backendFetch } from '@/lib/backendProxy';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

function resolveBackendUrl(): string {
    // Evaluated per request so test harnesses (and prod env mutations on
    // restart) pick up the latest value without re-importing the module.
    return (
        process.env.WORKSPACE_EVENTS_BACKEND_URL
        || process.env.BACKEND_PUBLIC_HOST
        || process.env.NEXT_PUBLIC_API_URL
        || process.env.BACKEND_URL
        || 'http://127.0.0.1:8000'
    );
}

export async function GET(req: Request): Promise<Response> {
    const upstreamUrl = `${resolveBackendUrl().replace(/\/$/, '')}/workspace/events`;

    // Pull the Supabase access token from the auth cookie as a fallback for
    // clients that do not send an explicit Authorization header.
    let accessToken: string | null = null;
    try {
        const supabase = await createClient();
        const { data: sessionData } = await supabase.auth.getSession();
        accessToken = sessionData.session?.access_token ?? null;
    } catch (err) {
        // Cookie store or Supabase client failure — fall through to upstream
        // attempt below; the existing Authorization header (if any) still
        // gets a chance to authenticate.
        console.error('[api/workspace/events] supabase session read failed:', err);
    }

    const headers: Record<string, string> = {
        accept: 'text/event-stream',
    };
    const cookie = req.headers.get('cookie');
    if (cookie) headers.cookie = cookie;
    const auth = req.headers.get('authorization');
    if (auth) {
        headers.authorization = auth;
    } else if (accessToken) {
        headers.authorization = `Bearer ${accessToken}`;
    }

    try {
        const upstream = await backendFetch(upstreamUrl, {
            method: 'GET',
            headers,
            // SSE streams must not be cached or buffered.
            cache: 'no-store',
        });

        if (!upstream.ok || !upstream.body) {
            return NextResponse.json(
                { error: `upstream returned ${upstream.status}` },
                { status: upstream.status || 502 },
            );
        }

        return new Response(upstream.body, {
            status: 200,
            headers: {
                'content-type': 'text/event-stream',
                'cache-control': 'no-cache, no-transform',
                connection: 'keep-alive',
                'x-accel-buffering': 'no',
            },
        });
    } catch (err) {
        return NextResponse.json(
            { error: 'workspace events upstream unavailable', detail: String(err) },
            { status: 502 },
        );
    }
}
