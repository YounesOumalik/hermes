/**
 * Hermes Gateway — BFF reverse proxy avec routing par préfixe.
 *
 * Architecture 4 couches :
 *   - /v1/*                  → hermes-llm-proxy (OpenAI-compat)
 *   - /api/llm/*             → hermes-llm-proxy (alias sémantique)
 *   - /api/orchestrator/*    → hermes-core (Phase 4+)
 *   - /api/conversations/*   → hermes-core
 *   - /api/agents/*          → hermes-core
 *   - /api/tools/*           → hermes-core (DB-backed registry)
 *   - /api/settings/*        → hermes-core
 *   - /api/runs/*            → hermes-core (Phase 4)
 *   - /api/approvals/*       → hermes-core (Phase 4)
 *   - /api/events/*          → hermes-core (Phase 4)
 *   - /api/system/*          → hermes-core (system status)
 *   - default                → hermes-llm-proxy (legacy compat)
 *
 * Phase 3 : routing + audit + user-id injection.
 */

import { NextRequest, NextResponse } from 'next/server';
import { verifySession, SESSION_COOKIE } from '../../../../lib/auth';

const LLM_PROXY_URL = (process.env.HERMES_LLM_PROXY_URL || 'http://hermes-llm-proxy:8001').replace(/\/$/, '');
const CORE_URL = (process.env.HERMES_CORE_URL || 'http://hermes-core:8002').replace(/\/$/, '');

const ROUTES: Record<string, string> = {
  '/v1/': LLM_PROXY_URL,
  '/api/llm/': LLM_PROXY_URL,
  '/api/orchestrator/': CORE_URL,
  '/api/conversations/': CORE_URL,
  '/api/agents/': CORE_URL,
  '/api/tools/': CORE_URL,
  '/api/settings/': CORE_URL,
  '/api/runs/': CORE_URL,
  '/api/approvals/': CORE_URL,
  '/api/events/': CORE_URL,
  '/api/system/': CORE_URL,
};

function pickUpstream(path: string): string {
  for (const prefix of Object.keys(ROUTES).sort((a, b) => b.length - a.length)) {
    if (path.startsWith(prefix)) return ROUTES[prefix];
  }
  // Fallback : LLM proxy (compat legacy)
  return LLM_PROXY_URL;
}

async function forward(request: NextRequest, path: string[]) {
  const joined = path.join('/');
  const upstream = pickUpstream('/' + joined);
  const target = `${upstream}/${joined}${request.nextUrl.search}`;

  const headers = new Headers();
  headers.set('Accept', request.headers.get('accept') || 'application/json');

  // Service token partagé
  const serviceToken = process.env.HERMES_SERVICE_TOKEN || process.env.HERMES_JWT_SECRET;
  if (serviceToken) headers.set('Authorization', `Bearer ${serviceToken}`);

  // Inject user-id depuis la session (pour audit/RBAC côté core)
  try {
    const sessionCookie = request.cookies.get(SESSION_COOKIE)?.value;
    if (sessionCookie) {
      const valid = await verifySession(sessionCookie);
      if (valid) {
        // Décode le username depuis le payload (format : base64url(username).expiresAt.signature)
        const [encodedUsername] = sessionCookie.split('.');
        if (encodedUsername) {
          // base64url decode
          const padded = encodedUsername.replace(/-/g, '+').replace(/_/g, '/') + '==='.slice((encodedUsername.length + 3) % 4);
          const username = Buffer.from(padded, 'base64').toString('utf8');
          headers.set('X-Hermes-User-Id', username);
          headers.set('X-Hermes-User-Roles', 'default');
        }
      }
    }
  } catch {
    // Session invalide → auth middleware aura déjà redirigé, on continue quand même
  }

  let body: BodyInit | undefined;
  if (!['GET', 'HEAD'].includes(request.method)) {
    body = await request.arrayBuffer();
    const ct = request.headers.get('content-type');
    if (ct) headers.set('Content-Type', ct);
  }

  const start = Date.now();
  try {
    const response = await fetch(target, {
      method: request.method,
      headers,
      body,
      cache: 'no-store',
      redirect: 'manual',
    });

    const contentType = response.headers.get('content-type') || '';

    // SSE pass-through : stream sans buffer (chat streaming + events)
    if (contentType.includes('text/event-stream') && response.body) {
      return new NextResponse(response.body, {
        status: response.status,
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive',
          'X-Accel-Buffering': 'no',
        },
      });
    }

    // Buffer normal (JSON / text)
    const responseBody = await response.text();
    const responseHeaders = new Headers({ 'Content-Type': contentType || 'application/json' });
    const location = response.headers.get('location');
    if (location) responseHeaders.set('Location', location);

    const duration = Date.now() - start;
    // Audit log (console only MVP — Phase 6 logging structuré)
    if (process.env.NODE_ENV !== 'production' || process.env.HERMES_AUDIT_LOG === 'true') {
      console.log(JSON.stringify({
        ts: new Date().toISOString(),
        user: headers.get('X-Hermes-User-Id') || 'anon',
        method: request.method,
        path: '/' + joined,
        upstream,
        status: response.status,
        duration_ms: duration,
      }));
    }

    return new NextResponse(responseBody, {
      status: response.status,
      headers: responseHeaders,
    });
  } catch (e) {
    console.error(`[gateway] ${request.method} /${joined} → ${upstream} failed:`, e);
    return NextResponse.json({ detail: 'Upstream service indisponible' }, { status: 502 });
  }
}

export async function GET(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return forward(request, (await context.params).path);
}

export async function POST(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return forward(request, (await context.params).path);
}

export async function PUT(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return forward(request, (await context.params).path);
}

export async function DELETE(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return forward(request, (await context.params).path);
}