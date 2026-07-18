/**
 * Hermes MCP Server — Serveur Model Context Protocol
 *
 * Expose des outils pour :
 *   • filesystem : lecture/écriture/listage dans /workspace
 *   • github     : opérations sur dépôts via Octokit
 *
 * Transport : Streamable HTTP sur le port 3100
 * Auth : Bearer token (MCP_AUTH_TOKEN)
 */

const express = require('express');
const cors = require('cors');
const fs = require('fs-extra');
const path = require('path');
const { execFile } = require('child_process');
const { promisify } = require('util');
const { Octokit } = require('octokit');

const execFileAsync = promisify(execFile);

const PORT = process.env.MCP_PORT || 3100;
const AUTH_TOKEN = process.env.MCP_AUTH_TOKEN || '';
const GITHUB_TOKEN = process.env.GITHUB_TOKEN || '';
const WORKSPACE_DIR = process.env.WORKSPACE_DIR || '/workspace';
const TERMINAL_MAX_OUTPUT = 64 * 1024;
const TERMINAL_MAX_TIMEOUT_MS = 120 * 1000;
const TERMINAL_COMMANDS = new Set(['ls', 'find', 'cat', 'head', 'tail', 'grep', 'rg', 'df', 'du', 'ps', 'python3', 'node', 'npm', 'git', 'curl', 'wget', 'bash', 'sh']);
const TERMINAL_CONFIRM_COMMANDS = new Set(['python3', 'node', 'npm', 'git', 'curl', 'wget', 'bash', 'sh']);
const TERMINAL_BLOCKED_ARGS = new Set(['-c', '--command', '--eval', '-e', '-p', '--print', '--exec']);

const app = express();
const allowedOrigins = (process.env.MCP_ALLOWED_ORIGINS || 'http://localhost:8001')
  .split(',')
  .map((origin) => origin.trim())
  .filter(Boolean);
app.use(cors({ origin: allowedOrigins, credentials: false }));
app.use(express.json());

// ---------------------------------------------------------------------------
// Auth middleware
// ---------------------------------------------------------------------------
function requireAuth(req, res, next) {
  if (!AUTH_TOKEN && process.env.NODE_ENV === 'development') return next();
  if (!AUTH_TOKEN) return res.status(503).json({ error: 'MCP_AUTH_TOKEN non configuré' });
  const auth = req.headers.authorization;
  if (!auth || !auth.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  const token = auth.slice(7);
  if (token !== AUTH_TOKEN) {
    return res.status(403).json({ error: 'Forbidden' });
  }
  next();
}

// ---------------------------------------------------------------------------
// Health check
// ---------------------------------------------------------------------------
app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'hermes-mcp-server', timestamp: new Date().toISOString() });
});

// ---------------------------------------------------------------------------
// Tool registry (MCP-compatible JSON Schema)
// ---------------------------------------------------------------------------
const TOOLS = {
  'mcp_filesystem': {
    name: 'mcp_filesystem',
    description: 'Opérations sur le système de fichiers dans le workspace',
    inputSchema: {
      type: 'object',
      properties: {
        operation: { type: 'string', enum: ['read', 'write', 'list', 'delete'] },
        path: { type: 'string', description: 'Chemin relatif dans /workspace' },
        content: { type: 'string', description: 'Contenu pour write' },
        confirmed: { type: 'boolean', description: 'Requis pour write/delete' },
      },
      required: ['operation', 'path'],
    },
  },
  'mcp_github': {
    name: 'mcp_github',
    description: 'Opérations GitHub (liste repos, lecture fichier, PR, recherche)',
    inputSchema: {
      type: 'object',
      properties: {
        operation: { type: 'string', enum: ['list_repos', 'read_file', 'create_pr', 'search_code'] },
        repo: { type: 'string', description: 'owner/name' },
        path: { type: 'string', description: 'Chemin du fichier' },
        branch: { type: 'string', description: 'Branche' },
        title: { type: 'string', description: 'Titre PR (create_pr)' },
        body: { type: 'string', description: 'Corps PR (create_pr)' },
        confirmed: { type: 'boolean', description: 'Requis pour create_pr' },
      },
      required: ['operation'],
    },
  },
  'mcp_terminal': {
    name: 'mcp_terminal',
    description: 'Exécute une commande contrôlée dans /workspace pour diagnostics et scripts',
    inputSchema: {
      type: 'object',
      properties: {
        command: { type: 'string', enum: [...TERMINAL_COMMANDS] },
        args: { type: 'array', items: { type: 'string' } },
        cwd: { type: 'string', description: 'Sous-dossier relatif à /workspace' },
        timeout_seconds: { type: 'integer', minimum: 1, maximum: 120 },
        confirmed: { type: 'boolean', description: 'Requis pour scripts, réseau et commandes mutantes' },
      },
      required: ['command'],
    },
  },
};

// ---------------------------------------------------------------------------
// MCP endpoints
// ---------------------------------------------------------------------------
app.get('/tools', requireAuth, (req, res) => {
  res.json({ tools: Object.values(TOOLS) });
});

app.post('/tools/:name/call', requireAuth, async (req, res) => {
  const { name } = req.params;
  const { arguments: args } = req.body;

  if (!TOOLS[name]) {
    return res.status(404).json({ error: `Tool inconnu: ${name}` });
  }

  try {
    if (name === 'mcp_filesystem') {
      if (['write', 'delete'].includes(args?.operation) && args?.confirmed !== true) {
        return res.json({ content: [{ type: 'text', text: JSON.stringify({ requires_confirmation: true, tool: name, message: 'Confirmation explicite requise pour modifier ou supprimer un fichier.' }) }] });
      }
      const result = await handleFilesystem(args);
      return res.json({ content: [{ type: 'text', text: JSON.stringify(result) }] });
    }
    if (name === 'mcp_github') {
      if (args?.operation === 'create_pr' && args?.confirmed !== true) {
        return res.json({ content: [{ type: 'text', text: JSON.stringify({ requires_confirmation: true, tool: name, message: 'Confirmation explicite requise pour créer une pull request.' }) }] });
      }
      const result = await handleGithub(args, req.headers['x-mcp-github-token'] || '');
      return res.json({ content: [{ type: 'text', text: JSON.stringify(result) }] });
    }
    if (name === 'mcp_terminal') {
      const result = await handleTerminal(args);
      return res.json({ content: [{ type: 'text', text: JSON.stringify(result) }] });
    }
    return res.status(400).json({ error: 'Tool non supporté' });
  } catch (err) {
    return res.status(500).json({ error: String(err) });
  }
});

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------
async function handleFilesystem(args) {
  const { operation, path: relPath, content } = args;
  const fullPath = path.resolve(WORKSPACE_DIR, relPath || '.');
  const relativePath = path.relative(WORKSPACE_DIR, fullPath);

  // Sécurité : empêcher la traversée de répertoire
  if (relativePath.startsWith('..') || path.isAbsolute(relativePath)) {
    throw new Error('Chemin non autorisé');
  }

  switch (operation) {
    case 'read':
      return { content: await fs.readFile(fullPath, 'utf8') };
    case 'write':
      await fs.ensureDir(path.dirname(fullPath));
      await fs.writeFile(fullPath, content, 'utf8');
      return { written: true, path: fullPath };
    case 'list':
      const items = await fs.readdir(fullPath, { withFileTypes: true });
      return {
        items: items.map((i) => ({ name: i.name, type: i.isDirectory() ? 'dir' : 'file' })),
      };
    case 'delete':
      await fs.remove(fullPath);
      return { deleted: true, path: fullPath };
    default:
      throw new Error(`Opération inconnue: ${operation}`);
  }
}

function resolveWorkspacePath(relativePath = '.') {
  if (typeof relativePath !== 'string' || relativePath.includes('\0') || path.isAbsolute(relativePath)) {
    throw new Error('Le chemin doit rester relatif au workspace.');
  }
  const fullPath = path.resolve(WORKSPACE_DIR, relativePath);
  const relative = path.relative(WORKSPACE_DIR, fullPath);
  if (relative.startsWith('..') || path.isAbsolute(relative)) {
    throw new Error('Chemin hors du workspace interdit.');
  }
  return fullPath;
}

function validateTerminalArgs(args) {
  if (!Array.isArray(args) || args.length > 40 || args.some((arg) => typeof arg !== 'string' || arg.length > 1000 || arg.includes('\0'))) {
    throw new Error('Arguments invalides ou trop nombreux.');
  }
  for (const arg of args) {
    if (TERMINAL_BLOCKED_ARGS.has(arg) || arg.startsWith('/') || arg.startsWith('~') || /(^|[\\/])\.\.([\\/]|$)/.test(arg)) {
      throw new Error('Argument shell ou chemin hors workspace interdit.');
    }
    if (/(^|[\\/])(?:\.env(?:\.|$)|id_rsa|credentials|secrets|.*\.(?:pem|key))([\\/]|$)/i.test(arg)) {
      throw new Error('Les fichiers de secrets ne peuvent pas être lus par le terminal Hermes.');
    }
  }
}

async function handleTerminal(args = {}) {
  const command = String(args.command || '');
  const commandArgs = args.args || [];
  if (!TERMINAL_COMMANDS.has(command)) throw new Error('Commande non autorisée.');
  validateTerminalArgs(commandArgs);
  if (TERMINAL_CONFIRM_COMMANDS.has(command) && args.confirmed !== true) {
    return {
      requires_confirmation: true,
      command,
      message: 'Cette commande peut exécuter du code, modifier le workspace ou accéder au réseau. Demande une confirmation explicite à l’utilisateur.',
    };
  }
  const cwd = resolveWorkspacePath(args.cwd || '.');
  const timeoutSeconds = Math.min(Math.max(Number(args.timeout_seconds) || 30, 1), 120);
  const safeEnv = {
    PATH: process.env.PATH || '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
    HOME: '/tmp/hermes-home',
    LANG: 'C.UTF-8',
    LC_ALL: 'C.UTF-8',
    NODE_ENV: 'production',
  };
  await fs.ensureDir(safeEnv.HOME);
  const startedAt = Date.now();
  try {
    const result = await execFileAsync(command, commandArgs, {
      cwd,
      env: safeEnv,
      shell: false,
      timeout: timeoutSeconds * 1000,
      maxBuffer: TERMINAL_MAX_OUTPUT,
      windowsHide: true,
    });
    return {
      ok: true,
      command,
      args: commandArgs,
      cwd,
      exit_code: 0,
      duration_ms: Date.now() - startedAt,
      stdout: String(result.stdout || '').slice(0, TERMINAL_MAX_OUTPUT),
      stderr: String(result.stderr || '').slice(0, TERMINAL_MAX_OUTPUT),
    };
  } catch (error) {
    return {
      ok: false,
      command,
      args: commandArgs,
      cwd,
      exit_code: Number.isInteger(error.code) ? error.code : null,
      timed_out: error.killed === true || error.signal === 'SIGTERM',
      duration_ms: Date.now() - startedAt,
      stdout: String(error.stdout || '').slice(0, TERMINAL_MAX_OUTPUT),
      stderr: String(error.stderr || error.message || '').slice(0, TERMINAL_MAX_OUTPUT),
    };
  }
}

async function handleGithub(args, requestToken = '') {
  const { operation, repo, path: filePath, branch, title, body } = args;

  const githubToken = requestToken || GITHUB_TOKEN;
  if (!githubToken) {
    throw new Error('GITHUB_TOKEN non configuré');
  }

  const octokit = new Octokit({ auth: githubToken });

  switch (operation) {
    case 'list_repos':
      const { data: repos } = await octokit.rest.repos.listForAuthenticatedUser();
      return { repos: repos.map((r) => ({ name: r.name, full_name: r.full_name })) };
    case 'read_file':
      const { data: file } = await octokit.rest.repos.getContent({ owner: repo.split('/')[0], repo: repo.split('/')[1], path: filePath, ref: branch });
      const content = Buffer.from(file.content, 'base64').toString('utf8');
      return { content, path: filePath };
    case 'create_pr':
      const [owner, repoName] = repo.split('/');
      const { data: pr } = await octokit.rest.pulls.create({ owner, repo: repoName, title, body, head: branch, base: 'main' });
      return { pr_number: pr.number, url: pr.html_url };
    case 'search_code':
      const { data: results } = await octokit.rest.search.code({ q: filePath });
      return { total: results.total_count, items: results.items.slice(0, 10).map((i) => ({ repo: i.repository.full_name, path: i.path })) };
    default:
      throw new Error(`Opération inconnue: ${operation}`);
  }
}

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------
app.listen(PORT, () => {
  console.log(`[MCP] Hermes MCP Server écoute sur :${PORT}`);
  console.log(`[MCP] Workspace: ${WORKSPACE_DIR}`);
  console.log(`[MCP] Auth: ${AUTH_TOKEN ? 'activée' : 'désactivée (dev)'}`);
});
