import { NextRequest, NextResponse } from 'next/server';

const daemonUrl = process.env.HERMES_DAEMON_URL || process.env.NEXT_PUBLIC_DAEMON_URL || 'http://localhost:8001';

async function forward(request: NextRequest, path: string[]) {
  const target = `${daemonUrl.replace(/\/$/, '')}/${path.join('/')}${request.nextUrl.search}`;
  const headers = new Headers();
  headers.set('Accept', 'application/json');

  const serviceToken = process.env.HERMES_SERVICE_TOKEN || process.env.HERMES_JWT_SECRET;
  if (serviceToken) headers.set('Authorization', `Bearer ${serviceToken}`);

  let body: string | undefined;
  if (!['GET', 'HEAD'].includes(request.method)) {
    body = await request.text();
    headers.set('Content-Type', request.headers.get('content-type') || 'application/json');
  }

  try {
    const response = await fetch(target, {
      method: request.method,
      headers,
      body,
      cache: 'no-store',
    });
    const responseBody = await response.text();
    return new NextResponse(responseBody, {
      status: response.status,
      headers: { 'Content-Type': response.headers.get('content-type') || 'application/json' },
    });
  } catch {
    return NextResponse.json({ detail: 'Hermes Daemon indisponible' }, { status: 502 });
  }
}

export async function GET(request: NextRequest, context: { params: { path: string[] } }) {
  return forward(request, context.params.path);
}

export async function POST(request: NextRequest, context: { params: { path: string[] } }) {
  return forward(request, context.params.path);
}

export async function DELETE(request: NextRequest, context: { params: { path: string[] } }) {
  return forward(request, context.params.path);
}
