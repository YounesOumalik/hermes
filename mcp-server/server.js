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
const { Octokit } = require('octokit');

const PORT = process.env.MCP_PORT || 3100;
const AUTH_TOKEN = process.env.MCP_AUTH_TOKEN || '';
const GITHUB_TOKEN = process.env.GITHUB_TOKEN || '';
const WORKSPACE_DIR = process.env.WORKSPACE_DIR || '/workspace';

const app = express();
app.use(cors());
app.use(express.json());

// ---------------------------------------------------------------------------
// Auth middleware
// ---------------------------------------------------------------------------
function requireAuth(req, res, next) {
  if (!AUTH_TOKEN) return next(); // Mode dev : pas d'auth
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
      },
      required: ['operation'],
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
      const result = await handleFilesystem(args);
      return res.json({ content: [{ type: 'text', text: JSON.stringify(result) }] });
    }
    if (name === 'mcp_github') {
      const result = await handleGithub(args);
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
  const fullPath = path.join(WORKSPACE_DIR, relPath);

  // Sécurité : empêcher la traversée de répertoire
  if (!fullPath.startsWith(WORKSPACE_DIR)) {
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

async function handleGithub(args) {
  const { operation, repo, path: filePath, branch, title, body } = args;

  if (!GITHUB_TOKEN) {
    throw new Error('GITHUB_TOKEN non configuré');
  }

  const octokit = new Octokit({ auth: GITHUB_TOKEN });

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
