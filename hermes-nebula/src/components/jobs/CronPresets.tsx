"use client";

/**
 * Presets cron usuels + helper de description lisible.
 * Le custom reste possible via input texte.
 */

export interface CronPreset {
  label: string;
  value: string;
  description: string;
}

export const CRON_PRESETS: CronPreset[] = [
  { label: "Every minute", value: "* * * * *", description: "Runs every minute" },
  { label: "Every hour", value: "0 * * * *", description: "Runs at minute 0 of every hour" },
  { label: "Every day at 9 AM", value: "0 9 * * *", description: "Runs daily at 09:00" },
  { label: "Every day at 6 PM", value: "0 18 * * *", description: "Runs daily at 18:00" },
  { label: "Every Monday 9 AM", value: "0 9 * * 1", description: "Runs every Monday at 09:00" },
  { label: "Every Friday 5 PM", value: "0 17 * * 5", description: "Runs every Friday at 17:00" },
  { label: "First of month 9 AM", value: "0 9 1 * *", description: "Runs on day 1 of each month at 09:00" },
];

/**
 * Conversion simplifiée cron → texte lisible (best-effort).
 * Pour les presets connus on retourne leur description.
 */
export function describeCron(expression: string): string {
  const preset = CRON_PRESETS.find((p) => p.value === expression);
  if (preset) return preset.description;

  // Tentative de parsing simplifiée pour les cas courants
  const parts = expression.trim().split(/\s+/);
  if (parts.length !== 5) return expression;

  const [min, hour, day, month, weekday] = parts;
  if (min === "*" && hour === "*") return "Every minute";
  if (min === "0" && hour === "*") return "Every hour";
  if (min === "0" && hour !== "*" && day === "*" && month === "*" && weekday === "*") {
    return `Every day at ${pad(hour)}:00`;
  }
  return expression;
}

function pad(n: string): string {
  const num = parseInt(n, 10);
  if (isNaN(num)) return n;
  return num < 10 ? `0${num}` : `${num}`;
}
