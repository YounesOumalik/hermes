"use client";

import { useEffect, useState } from "react";
import { Modal, Spinner, Badge } from "@/components/ui";
import { apiGet } from "@/lib/api";
import type { Job, JobRun } from "@/lib/types";

interface JobRunHistoryProps {
  open: boolean;
  onClose: () => void;
  job: Job | null;
}

/**
 * Modal listant les exécutions passées d'un job (JobRun[]).
 */
export function JobRunHistory({ open, onClose, job }: JobRunHistoryProps) {
  const [runs, setRuns] = useState<JobRun[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !job) return;
    let cancelled = false;
    setIsLoading(true);
    setError(null);
    apiGet<JobRun[]>(`/jobs/${job.id}/runs`)
      .then((data) => {
        if (cancelled) return;
        setRuns(data);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : "Failed to load runs");
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, job]);

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={job ? `Run history — ${job.name}` : "Run history"}
      description="Latest executions of this scheduled job."
      size="md"
    >
      {isLoading ? (
        <div style={{ padding: "24px", display: "flex", justifyContent: "center" }}>
          <Spinner label="Loading runs..." />
        </div>
      ) : error ? (
        <p className="input-message input-message-error">{error}</p>
      ) : runs.length === 0 ? (
        <p style={{ color: "var(--text-muted)", fontSize: "14px", padding: "16px 0" }}>
          No runs yet. Click "Run now" on the job to trigger one.
        </p>
      ) : (
        <ul className="job-run-list">
          {runs.map((run) => (
            <li key={run.id} className="job-run-item">
              <div className="job-run-header">
                <Badge variant={runStatusVariant(run.status)}>{run.status}</Badge>
                <span className="job-run-date">
                  {run.started_at ? new Date(run.started_at).toLocaleString() : "—"}
                </span>
              </div>
              {run.error && <p className="job-run-error">{run.error}</p>}
              {run.finished_at && (
                <span className="job-run-duration">
                  Duration: {formatDuration(run.started_at, run.finished_at)}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </Modal>
  );
}

function runStatusVariant(status: JobRun["status"]): "success" | "error" | "pending" | "info" {
  switch (status) {
    case "success":
      return "success";
    case "failed":
      return "error";
    case "running":
      return "info";
    default:
      return "pending";
  }
}

function formatDuration(startIso: string | null, endIso: string | null): string {
  if (!startIso || !endIso) return "—";
  const start = new Date(startIso).getTime();
  const end = new Date(endIso).getTime();
  const ms = end - start;
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}min`;
}

export default JobRunHistory;
