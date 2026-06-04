import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  const token = request.nextUrl.searchParams.get('token')?.trim();
  if (!token) {
    return NextResponse.json(
      { message: 'Invite token is required.' },
      { status: 400 },
    );
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 5000);

  try {
    const upstream = await fetch(
      `${API_BASE_URL}/teams/invites/details?token=${encodeURIComponent(token)}`,
      {
        cache: 'no-store',
        signal: controller.signal,
      },
    );
    const body = await upstream.text();

    return new NextResponse(body, {
      status: upstream.status,
      headers: {
        'Content-Type': upstream.headers.get('content-type') ?? 'application/json',
      },
    });
  } catch (error) {
    const message = error instanceof Error && error.name === 'AbortError'
      ? 'Invitation lookup timed out.'
      : 'Failed to load invitation details.';

    return NextResponse.json({ message }, { status: 502 });
  } finally {
    clearTimeout(timeout);
  }
}
