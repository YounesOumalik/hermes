"use client";

import { useEffect, useState } from "react";
import { User } from "lucide-react";
import { Input, Button } from "@/components/ui";
import { apiPatch } from "@/lib/api";
import { useAuth } from "@/stores/authStore";
import type { User as UserType } from "@/lib/types";

/**
 * Onglet Profile : display name + username + avatar URL.
 */
export function ProfileTab() {
  const { user, setUser } = useAuth();
  const [displayName, setDisplayName] = useState(user?.display_name || "");
  const [username, setUsername] = useState(user?.username || "");
  const [avatarUrl, setAvatarUrl] = useState(user?.avatar_url || "");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Resync si le user change
  useEffect(() => {
    if (user) {
      setDisplayName(user.display_name);
      setUsername(user.username || "");
      setAvatarUrl(user.avatar_url || "");
    }
  }, [user]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSaving) return;
    setIsSaving(true);
    setError(null);
    setSuccess(false);
    try {
      const updated = await apiPatch<UserType>("/settings/profile", {
        display_name: displayName,
        username: username || null,
        avatar_url: avatarUrl || null,
      });
      setUser(updated);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 2500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save profile");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <form onSubmit={handleSave} className="settings-form">
      <div className="settings-section">
        <div className="settings-section-header">
          <User size={16} />
          <h3 className="settings-section-title">Profile</h3>
        </div>

        <Input
          label="Email"
          value={user?.email || ""}
          disabled
          hint="Email cannot be changed."
        />

        <Input
          label="Display Name"
          name="display-name"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          placeholder="Your name"
        />

        <Input
          label="Username"
          name="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="@younes"
        />

        <Input
          label="Avatar URL"
          name="avatar-url"
          value={avatarUrl}
          onChange={(e) => setAvatarUrl(e.target.value)}
          placeholder="https://..."
        />
      </div>

      {error && <span className="input-message input-message-error">{error}</span>}
      {success && (
        <span className="input-message" style={{ color: "var(--color-success)" }}>
          ✓ Profile saved
        </span>
      )}

      <div className="settings-actions">
        <Button type="submit" loading={isSaving} disabled={isSaving}>
          Save changes
        </Button>
      </div>
    </form>
  );
}

export default ProfileTab;
