"use client";

import { useEffect, useState, useCallback } from "react";
import { Plus, Clock } from "lucide-react";
import "../globals.css";
import { AppShell } from "@/components/layout";
import { Button, EmptyState, ErrorState, Spinner } from "@/components/ui";
import { JobCard, CreateJobModal, JobRunHistory } from "@/components/jobs";
import { useWorkspaceStore } from "@/stores/workspaceStore";
import { apiGet, apiPost, apiPatch, apiDelete } from "@/lib/api";
import type { Agent, Job } from "@/lib/types";

export default function JobsPage() {
  const { activeWorkspace } = useWorkspaceStore();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [historyJob, setHistoryJob] = useState<Job | null>(null);

  const loadJobs = useCallback(async () => {
    if (!activeWorkspace) return;
    setIsLoading(true);
    setError(null);
    try {
      const [jobsData, agentsData] = await Promise.all([
        apiGet<Job[]>(`/workspaces/${activeWorkspace.id}/jobs`),
        apiGet<Agent[]>(`/workspaces/${activeWorkspace.id}/agents`),
      ]);
      setJobs(jobsData);
      setAgents(agentsData);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load jobs");
    } finally {
      setIsLoading(false);
    }
  }, [activeWorkspace]);

  useEffect(() => {
    loadJobs();
  }, [loadJobs]);

  const handleRunNow = async (job: Job) => {
    try {
      await apiPost(`/jobs/${job.id}/run-now`, {});
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to trigger job");
    }
  };

  const handleTogglePause = async (job: Job) => {
    const newStatus = job.status === "active" ? "paused" : "active";
    try {
      await apiPatch<Job>(`/jobs/${job.id}`, { status: newStatus });
      setJobs((prev) =>
        prev.map((j) => (j.id === job.id ? { ...j, status: newStatus } : j))
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update job");
    }
  };

  const handleDelete = async (job: Job) => {
    try {
      await apiDelete(`/jobs/${job.id}`);
      setJobs((prev) => prev.filter((j) => j.id !== job.id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete job");
    }
  };

  const handleCreated = (job: Job) => {
    setJobs((prev) => [job, ...prev]);
  };

  return (
    <AppShell title="Jobs">
      <div className="page-container">
        <div className="page-header">
          <div>
            <h1 className="page-title">Scheduled Jobs</h1>
            <p className="page-subtitle">
              {activeWorkspace
                ? `${activeWorkspace.name} · ${jobs.length} job${jobs.length !== 1 ? "s" : ""}`
                : "Select a workspace"}
            </p>
          </div>
          <Button
            variant="primary"
            icon={<Plus size={14} />}
            onClick={() => setIsCreateModalOpen(true)}
            disabled={!activeWorkspace || agents.length === 0}
            title={!activeWorkspace ? "Select a workspace first" : agents.length === 0 ? "Create an agent first" : undefined}
          >
            New Job
          </Button>
        </div>

        {error && (
          <ErrorState
            message={error}
            onRetry={() => {
              setError(null);
              loadJobs();
            }}
          />
        )}

        {isLoading ? (
          <div style={{ padding: "48px", display: "flex", justifyContent: "center" }}>
            <Spinner label="Loading jobs..." />
          </div>
        ) : !activeWorkspace ? (
          <EmptyState
            icon={<Clock size={48} />}
            title="No workspace selected"
            description="Select a workspace from the top bar to see its scheduled jobs."
          />
        ) : jobs.length === 0 ? (
          <EmptyState
            icon={<Clock size={48} />}
            title="No jobs yet"
            description={
              agents.length === 0
                ? "Create an agent first, then schedule a job to run it automatically."
                : "Create your first scheduled job to automate recurring agent tasks."
            }
            action={
              agents.length > 0 && (
                <Button
                  variant="primary"
                  icon={<Plus size={14} />}
                  onClick={() => setIsCreateModalOpen(true)}
                >
                  Create Job
                </Button>
              )
            }
          />
        ) : (
          <div className="jobs-grid">
            {jobs.map((job) => (
              <JobCard
                key={job.id}
                job={job}
                onRunNow={handleRunNow}
                onTogglePause={handleTogglePause}
                onDelete={handleDelete}
                onShowHistory={(j) => setHistoryJob(j)}
              />
            ))}
          </div>
        )}

        {activeWorkspace && (
          <CreateJobModal
            open={isCreateModalOpen}
            onClose={() => setIsCreateModalOpen(false)}
            workspaceId={activeWorkspace.id}
            agents={agents}
            onCreated={handleCreated}
          />
        )}

        <JobRunHistory
          open={!!historyJob}
          onClose={() => setHistoryJob(null)}
          job={historyJob}
        />
      </div>
    </AppShell>
  );
}
