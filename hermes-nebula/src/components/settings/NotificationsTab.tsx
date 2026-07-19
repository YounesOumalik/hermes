"use client";

import { useEffect, useState } from "react";
import { Bell, Check } from "lucide-react";
import { Card, Badge, Spinner } from "@/components/ui";
import { apiGet, apiPatch } from "@/lib/api";
import type { NotificationChannel } from "@/lib/types";

/**
 * Onglet Notifications : liste des channels (email/webhook/slack/...) avec toggle actif.
 */
export function NotificationsTab() {
  const [channels, setChannels] = useState<NotificationChannel[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const load = () => {
    setIsLoading(true);
    setError(null);
    apiGet<NotificationChannel[]>("/settings/notifications/channels")
      .then(setChannels)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load channels"))
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const toggleChannel = async (channel: NotificationChannel) => {
    setUpdatingId(channel.id);
    try {
      const updated = await apiPatch<NotificationChannel>(
        `/settings/notifications/channels/${channel.id}`,
        { is_active: !channel.is_active }
      );
      setChannels((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update channel");
    } finally {
      setUpdatingId(null);
    }
  };

  if (isLoading) {
    return (
      <div style={{ padding: "24px", display: "flex", justifyContent: "center" }}>
        <Spinner label="Loading channels..." />
      </div>
    );
  }

  return (
    <div className="settings-section">
      <div className="settings-section-header">
        <Bell size={16} />
        <h3 className="settings-section-title">Notification Channels</h3>
      </div>

      {error && <p className="input-message input-message-error">{error}</p>}

      {channels.length === 0 ? (
        <p className="settings-empty">
          No notification channel configured. Contact an admin to set one up.
        </p>
      ) : (
        <div className="notifications-list">
          {channels.map((channel) => (
            <Card key={channel.id} variant="flat" padding="md">
              <div className="notification-item">
                <div className="notification-info">
                  <div className="notification-label-row">
                    <h4 className="notification-label">{channel.label}</h4>
                    <Badge variant={channel.is_active ? "success" : "default"}>
                      {channel.is_active ? "Active" : "Disabled"}
                    </Badge>
                  </div>
                  <p className="notification-type">Type: {channel.type}</p>
                </div>
                <button
                  type="button"
                  className={`btn ${channel.is_active ? "btn-secondary" : "btn-primary"} btn-size-sm`}
                  onClick={() => toggleChannel(channel)}
                  disabled={updatingId === channel.id}
                >
                  {channel.is_active ? "Disable" : "Enable"}
                  {channel.is_active && <Check size={12} />}
                </button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

export default NotificationsTab;
