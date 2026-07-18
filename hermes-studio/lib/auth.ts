const SESSION_COOKIE = 'hermes_session';
const SESSION_TTL_SECONDS = 60 * 60 * 8;

function toBase64Url(bytes: Uint8Array) {
  let binary = '';
  bytes.forEach((byte) => { binary += String.fromCharCode(byte); });
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}

function fromBase64Url(value: string) {
  const padded = value.replace(/-/g, '+').replace(/_/g, '/') + '==='.slice((value.length + 3) % 4);
  const binary = atob(padded);
  return Uint8Array.from(binary, (character) => character.charCodeAt(0));
}

async function getKey() {
  const secret = process.env.HERMES_SESSION_SECRET || process.env.HERMES_JWT_SECRET || (process.env.NODE_ENV !== 'production' ? 'dev-secret-key-1234567890123456' : null);
  if (!secret) return null;
  return crypto.subtle.importKey('raw', new TextEncoder().encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign', 'verify']);
}

export async function createSession(username: string) {
  const key = await getKey();
  if (!key) throw new Error('HERMES_SESSION_SECRET is not configured');
  const encodedUsername = toBase64Url(new TextEncoder().encode(username));
  const expiresAt = Math.floor(Date.now() / 1000) + SESSION_TTL_SECONDS;
  const payload = `${encodedUsername}.${expiresAt}`;
  const signature = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(payload));
  return `${payload}.${toBase64Url(new Uint8Array(signature))}`;
}

export async function verifySession(value?: string) {
  if (!value) return false;
  const [encodedUsername, expiresAt, signature] = value.split('.');
  if (!encodedUsername || !expiresAt || !signature || Number(expiresAt) < Math.floor(Date.now() / 1000)) return false;
  try {
    const key = await getKey();
    if (!key) return false;
    return crypto.subtle.verify('HMAC', key, fromBase64Url(signature), new TextEncoder().encode(`${encodedUsername}.${expiresAt}`));
  } catch {
    return false;
  }
}

export { SESSION_COOKIE, SESSION_TTL_SECONDS };
