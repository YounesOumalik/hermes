"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import "./globals.css";
import { Sidebar, ChatPanel, WorkspaceModal, AgentModal } from "@/components/dashboard";
import { TopBar } from "@/components/layout";
import { EmptyState } from "@/components/ui";
import { Bot } from "lucide-react";
import { useAuth } from "@/stores/authStore";
import { useWorkspaceStore } from "@/stores/workspaceStore";
import { apiFetch, apiGet, apiPost, isAuthenticated } from "@/lib/api";
import type { Agent, Conversation, Message, ModelConfig } from "@/lib/types";

/**
 * Page dashboard principale.
 * Orchestrateur qui assemble :
 *   <Sidebar />  <ChatPanel />  + modals
 *
 * Le state reste local ici car il est partagé entre Sidebar et ChatPanel.
 * (Lifting state up pattern.)
 */
export default function WorkspaceDashboard() {
  const router = useRouter();
  const { user, fetchUser, isInitialized } = useAuth();
  const { activeWorkspace, fetchWorkspaces } = useWorkspaceStore();

  const [agents, setAgents] = useState<Agent[]>([]);
  const [activeAgent, setActiveAgent] = useState<Agent | null>(null);

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversation, setActiveConversation] = useState<Conversation | null>(null);

  const [messages, setMessages] = useState<Message[]>([]);

  const [availableModels, setAvailableModels] = useState<ModelConfig[]>([]);

  const [isWorkspaceModalOpen, setIsWorkspaceModalOpen] = useState(false);
  const [isAgentModalOpen, setIsAgentModalOpen] = useState(false);

  // --- Boot : auth + workspaces -----------------------------------------
  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
      return;
    }
    if (!isInitialized) {
      fetchUser();
    }
    fetchWorkspaces();
    // Charger aussi la liste des modèles AI disponibles
    apiGet<ModelConfig[]>("/models")
      .then(setAvailableModels)
      .catch(() => setAvailableModels([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router]);

  // --- Charger les agents quand le workspace change ---------------------
  useEffect(() => {
    if (!activeWorkspace) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await apiFetch(`/workspaces/${activeWorkspace.id}/agents`);
        if (cancelled) return;
        if (res.ok) {
          const data: Agent[] = await res.json();
          setAgents(data);
          if (data.length > 0) {
            setActiveAgent(data[0]);
          } else {
            setActiveAgent(null);
            setConversations([]);
            setActiveConversation(null);
            setMessages([]);
          }
        }
      } catch {
        // silent — sidebar affichera l'état vide
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [activeWorkspace]);

  // --- Charger les conversations quand l'agent change -------------------
  useEffect(() => {
    if (!activeAgent) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await apiFetch(`/agents/${activeAgent.id}/conversations`);
        if (cancelled) return;
        if (res.ok) {
          const data: Conversation[] = await res.json();
          setConversations(data);
          if (data.length > 0) {
            setActiveConversation(data[0]);
            return;
          }
          // Aucune conversation → en créer une maintenant (bloquant)
          // pour que l'input soit immédiatement utilisable.
          try {
            const created = await apiPost<Conversation>(
              `/agents/${activeAgent.id}/conversations`,
              {
                agent_id: activeAgent.id,
                title: "New chat thread",
              }
            );
            if (cancelled) return;
            setConversations([created]);
            setActiveConversation(created);
          } catch {
            if (!cancelled) {
              setActiveConversation(null);
            }
          }
        }
      } catch {
        // silent
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeAgent]);

  // --- Charger les messages quand la conversation change ----------------
  useEffect(() => {
    if (!activeConversation) {
      setMessages([]);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const res = await apiFetch(`/conversations/${activeConversation.id}/messages`);
        if (cancelled) return;
        if (res.ok) {
          setMessages(await res.json());
        }
      } catch {
        // silent
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [activeConversation]);

  // --- Actions ----------------------------------------------------------
  const createConversation = async (agentId: string) => {
    try {
      const created = await apiPost<Conversation>(
        `/agents/${agentId}/conversations`,
        {
          agent_id: agentId,
          title: "New chat thread",
        }
      );
      setConversations((prev) => [created, ...prev]);
      setActiveConversation(created);
    } catch {
      // silent
    }
  };

  const handleAgentCreated = (agent: Agent) => {
    setAgents((prev) => [...prev, agent]);
    setActiveAgent(agent);
  };

  const handleAgentChanged = (updated: Agent) => {
    setAgents((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
    setActiveAgent(updated);
  };

  // --- Render -----------------------------------------------------------
  return (
    <>
      <TopBar title={activeAgent?.name || "Dashboard"} />
      <div className="main-wrapper">
        <Sidebar
          agents={agents}
          activeAgentId={activeAgent?.id || null}
          onSelectAgent={setActiveAgent}
          onOpenWorkspaceModal={() => setIsWorkspaceModalOpen(true)}
          onOpenAgentModal={() => setIsAgentModalOpen(true)}
        />

        <section
          style={{ flex: 1, display: "flex", flexDirection: "column", height: "100vh" }}
        >
          {activeAgent ? (
            <ChatPanel
              agent={activeAgent}
              conversation={activeConversation}
              conversations={conversations}
              messages={messages}
              availableModels={availableModels}
              onSelectConversation={setActiveConversation}
              onMessagesChange={setMessages}
              onCreateConversation={() => createConversation(activeAgent.id)}
              onAgentChanged={handleAgentChanged}
            />
          ) : (
            <EmptyState
              icon={<Bot size={48} />}
              title="No agent selected"
              description="Create or select an agent in the sidebar to start collaborating."
              action={
                activeWorkspace && (
                  <button
                    className="btn btn-primary btn-size-md"
                    onClick={() => setIsAgentModalOpen(true)}
                  >
                    Create an Agent
                  </button>
                )
              }
            />
          )}
        </section>

        <WorkspaceModal
          open={isWorkspaceModalOpen}
          onClose={() => setIsWorkspaceModalOpen(false)}
        />

        {activeWorkspace && (
          <AgentModal
            open={isAgentModalOpen}
            onClose={() => setIsAgentModalOpen(false)}
            workspaceId={activeWorkspace.id}
            onCreated={handleAgentCreated}
          />
        )}

        {/* Legacy spinner keyframes — désormais dans globals.css via .btn-spinner */}
        <style jsx global>{`
          @keyframes spin {
            to { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    </>
  );
}
