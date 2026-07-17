export default function HomePage() {
  return (
    <div>
      <h1>Hermes Studio</h1>
      <p className="card">
        Plateforme d&apos;orchestration multi-agents. Connectez Minimax, déléguez
        à n8n, et accédez au système via MCP.
      </p>
      <div className="card">
        <h2>Démarrage rapide</h2>
        <ol>
          <li>Configurez votre clé API Minimax dans <a href="/settings">Settings</a></li>
          <li>Créez un agent dans <a href="/agents">Agents</a></li>
          <li>Testez dans <a href="/chat">Chat</a></li>
          <li>Gérez les outils dans <a href="/tools">Tools</a></li>
        </ol>
      </div>
    </div>
  );
}
