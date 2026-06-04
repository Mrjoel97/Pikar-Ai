// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { backendFetch } from '@/lib/backendProxy';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

function resolveBackendUrl(): string {
  return (
    process.env.BACKEND_PUBLIC_HOST
    || process.env.NEXT_PUBLIC_API_URL
    || process.env.BACKEND_URL
    || 'http://localhost:8000'
  ).replace(/\/+$/, '');
}

export async function GET(request: NextRequest): Promise<NextResponse> {
  let authorization = request.headers.get('authorization');

  if (!authorization) {
    const supabase = await createClient();
    const { data } = await supabase.auth.getSession();
    if (data.session?.access_token) {
      authorization = `Bearer ${data.session.access_token}`;
    }
  }

  if (!authorization) {
    return NextResponse.json({ access: false });
  }

  try {
    const upstream = await backendFetch(`${resolveBackendUrl()}/admin/check-access`, {
      headers: { authorization },
      cache: 'no-store',
    });

    if (upstream.ok) {
      return NextResponse.json(await upstream.json());
    }

    if (upstream.status === 401 || upstream.status === 403) {
      return NextResponse.json({ access: false });
    }

    console.error('[api/admin/check-access] backend returned', upstream.status);
    return NextResponse.json(
      { access: false, error: 'upstream_error' },
      { status: 502 },
    );
  } catch (err) {
    console.error('[api/admin/check-access] threw:', err);
    return NextResponse.json(
      { access: false, error: 'internal' },
      { status: 500 },
    );
  }
}
