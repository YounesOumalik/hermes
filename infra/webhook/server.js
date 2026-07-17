#!/usr/bin/env node
/**
 * Hermes Orchestration — Webhook Receiver
 *
 * Adapté du pattern eaumalik.com. Écoute sur le port 9000, vérifie la
 * signature HMAC SHA-256, et déclenche deploy-on-push.sh pour relancer
 * le docker-compose de la stack d'orchestration.
 *
 * Transport : Caddy reverse_proxy /webhook → 127.0.0.1:9000
 * Auth       : HMAC SHA-256 (secret partagé GitHub ↔ VPS)
 */

import { createServer } from 'node:http';
import { spawn } from 'node:child_process';
import { readFileSync, existsSync, appendFileSync } from 'node:fs';
import { createHmac, timingSafeEqual } from 'node:crypto';

const PORT = 9000;
const WEBHOOK_SECRET_FILE = '/etc/eaumalik/hermes-webhook-secret';
const DEPLOY_SCRIPT = '/opt/hermes-orchestration/deploy-on-push.sh';
const LOG_FILE = '/var/log/hermes-webhook.log';

function log(level, msg) {
  const line = `[${new Date().toISOString()}] [${level}] ${msg}\n`;
  process.stdout.write(line);
  try { appendFileSync(LOG_FILE, line); } catch {}
}

function loadSecret() {
  if (!existsSync(WEBHOOK_SECRET_FILE)) {
    log('ERROR', `Secret file missing: ${WEBHOOK_SECRET_FILE}`);
    process.exit(1);
  }
  return readFileSync(WEBHOOK_SECRET_FILE, 'utf8').trim();
}

function verifySignature(secret, signatureHeader, rawBody) {
  if (!signatureHeader?.startsWith('sha256=')) return false;
  const computed = createHmac('sha256', secret).update(rawBody).digest('hex');
  const provided = signatureHeader.slice(7);
  if (provided.length !== computed.length) return false;
  return timingSafeEqual(Buffer.from(provided), Buffer.from(computed));
}

const server = createServer(async (req, res) => {
  // Health check (Caddy + monitoring)
  if (req.method === 'GET' && req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok', service: 'hermes-webhook' }));
    return;
  }

  // Webhook GitHub
  if (req.method === 'POST' && req.url === '/webhook') {
    const chunks = [];
    for await (const chunk of req) chunks.push(chunk);
    const rawBody = Buffer.concat(chunks).toString('utf8');

    if (!verifySignature(loadSecret(), req.headers['x-hub-signature-256'], rawBody)) {
      log('WARN', `Invalid signature from ${req.socket.remoteAddress}`);
      res.writeHead(401, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Invalid signature' }));
      return;
    }

    const event = req.headers['x-github-event'];
    if (event !== 'push') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ status: 'ignored', event }));
      return;
    }

    let payload;
    try { payload = JSON.parse(rawBody); } catch {
      res.writeHead(400).end('{}');
      return;
    }

    if (payload.ref !== 'refs/heads/main') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ status: 'ignored', ref: payload.ref }));
      return;
    }

    const sha = (payload.after || '').slice(0, 7);
    const pusher = payload.pusher?.name || 'unknown';
    log('INFO', `Deploy requested by ${pusher} (commit ${sha})`);

    // Répondre immédiatement à GitHub (202 Accepted)
    res.writeHead(202, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'deploying', sha }));

    // Lancer le déploiement en arrière-plan
    const child = spawn('bash', [DEPLOY_SCRIPT, sha], {
      env: { ...process.env, DEPLOY_SHA: sha, DEPLOY_PUSHER: pusher },
      detached: true,
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    child.unref();

    child.stdout.on('data', (d) => log('DEPLOY', `[stdout] ${d.toString().trim()}`));
    child.stderr.on('data', (d) => log('DEPLOY', `[stderr] ${d.toString().trim()}`));
    child.on('exit', (code) => log(code === 0 ? 'INFO' : 'ERROR', `Deploy ${sha} exit=${code}`));
    return;
  }

  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'Not found' }));
});

server.listen(PORT, () => log('INFO', `Hermes webhook listening on :${PORT}`));
