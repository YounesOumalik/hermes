"use client";

import { Play, Pause, Trash2, Clock, History } from "lucide-react";
import { Card, Badge } from "@/components/ui";
import { describeCron } from "./CronPresets";
import type { Job } from "@/lib/types";

interface JobCardProps {
  job: Job;
  onRunNow?: (job: Job) => void;
  onTogglePause?: (job: Job) => void;
  onDelete?: (job: Job) => void;
  onShowHistory?: (job: Job) => void;
}

/**
 * Carte d'un job planifié.
 */
export function JobCard({
  job,
  onRunNow,
  onTogglePause,
  onDelete,
  onShowHistory,
}: JobCardProps) {
  const isActive = job.status === "active";
  const nextRunLabel = job.next_run_at
    ? formatNextRun(job.next_run_at)
    : "Not scheduled";

  const handleRunNow = () => onRunNow?.(job);
  const handleToggle = () => onTogglePause?.(job);
  const handleDelete = () => {
    if (window.confirm(`Delete job "${job.name}"? This cannot be undone.`)) {
      onDelete?.(job);
    }
  };
  const handleHistory = () => onShowHistory?.(job);

  return (
    <Card variant="glass" padding="md" hoverable>
      <div className="job-card">
        <div className="job-card-header">
          <div className="job-card-title-row">
            <h3 className="job-card-title">{job.name}</h3>
            <Badge variant={isActive ? "success" : "pending"}>
              {isActive ? "Active" : job.status === "paused" ? "Paused" : job.status}
            </Badge>
          </div>
          <p className="job-card-prompt" title={job.prompt}>
            {job.prompt}
          </p>
        </div>

        <div className="job-card-meta">
          <div className="job-card-cron">
            <Clock size={12} />
            <code className="job-card-cron-expr">{job.cron_expression}</code>
            <span className="job-card-cron-desc">{describeCron(job.cron_expression)}</span>
          </div>
          <p className="job-card-next-run">Next: {nextRunLabel}</p>
        </div>

        <div className="job-card-actions">
          <button
            type="button"
            className="btn btn-ghost btn-size-sm"
            onClick={handleHistory}
            disabled={!onShowHistory}
            title="Run history"
          >
            <History size={14} />
            History
          </button>
          <button
            type="button"
            className="btn btn-ghost btn-size-sm"
            onClick={handleRunNow}
            disabled={!isActive || !onRunNow}
            title="Run now"
          >
            <Play size={14} />
            Run now
          </button>
          <button
            type="button"
            className="btn btn-ghost btn-size-sm"
            onClick={handleToggle}
            disabled={!onTogglePause}
            title={isActive ? "Pause" : "Resume"}
          >
            {isActive ? <Pause size={14} /> : <Play size={14} />}
            {isActive ? "Pause" : "Resume"}
          </button>
          <button
            type="button"
            className="btn btn-ghost btn-size-sm btn-danger-ghost"
            onClick={handleDelete}
            disabled={!onDelete}
            title="Delete"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>
    </Card>
  );
}

function formatNextRun(isoDate: string): string {
  try {
    const date = new Date(isoDate);
    const now = new Date();
    const diffMs = date.getTime() - now.getTime();
    if (diffMs < 0) return "Pending";

    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 60) return `in ${diffMin}m`;
    const diffHours = Math.floor(diffMin / 60);
    if (diffHours < 24) return `in ${diffHours}h ${diffMin % 60}m`;
    const diffDays = Math.floor(diffHours / 24);
    return `in ${diffDays}d`;
  } catch {
    return isoDate;
  }
}

export default JobCard;
