import { scrypt as scryptCallback, timingSafeEqual } from 'node:crypto';
import { NextResponse } from 'next/server';
import { createSession, SESSION_COOKIE, SESSION_TTL_SECONDS } from '../../../../lib/auth';

export const runtime = 'nodejs';

function deriveKey(password: string, salt: Buffer, length: number) {
  return new Promise<Buffer>((resolve, reject) => {
    scryptCallback(password, salt, length, { N: 16384, r: 8, p: 1 }, (error, derived) => {
      if (error) reject(error);
      else resolve(derived as Buffer);
    });
  });
}

async function verifyPassword(password: string, encodedHash: string) {
  const [algorithm, saltEncoded, hashEncoded] = encodedHash.split('$');
  if (algorithm !== 'scrypt' || !saltEncoded || !hashEncoded) return false;
  try {
    const salt = Buffer.from(saltEncoded, 'base64url');
    const expected = Buffer.from(hashEncoded, 'base64url');
    const derived = await deriveKey(password, salt, expected.length || 64);
    return expected.length === derived.length && timingSafeEqual(expected, derived);
  } catch {
    return false;
  }
}

export async function POST(request: Request) {
  const configuredUsername = process.env.HERMES_ADMIN_USERNAME || 'admin';
  const configuredHash = process.env.HERMES_ADMIN_PASSWORD_HASH;
  if (process.env.NODE_ENV === 'production' && (!configuredHash?.startsWith('scrypt$') || (!process.env.HERMES_SESSION_SECRET && !process.env.HERMES_JWT_SECRET))) {
    return NextResponse.json({ detail: 'Authentification non configurée côté serveur' }, { status: 503 });
  }

  let credentials: { username?: string; password?: string };
  try {
    credentials = await request.json();
  } catch {
    return NextResponse.json({ detail: 'Requête invalide' }, { status: 400 });
  }

  const validUsername = credentials.username === configuredUsername || credentials.username === 'admin';
  
  let validPassword = false;
  if (process.env.NODE_ENV !== 'production' && !configuredHash) {
    validPassword = credentials.password === 'admin';
  } else {
    validPassword = typeof credentials.password === 'string' && await verifyPassword(credentials.password, configuredHash!);
  }
  
  if (!validUsername || !validPassword) return NextResponse.json({ detail: 'Identifiant ou mot de passe incorrect' }, { status: 401 });

  const response = NextResponse.json({ ok: true });
  response.cookies.set(SESSION_COOKIE, await createSession(configuredUsername), {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge: SESSION_TTL_SECONDS,
  });
  return response;
}
