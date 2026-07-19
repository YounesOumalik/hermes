"use client";

import { User, Bell, Shield } from "lucide-react";
import "../globals.css";
import { AppShell } from "@/components/layout";
import { Tabs } from "@/components/ui";
import { ProfileTab, NotificationsTab, SecurityTab } from "@/components/settings";

export default function SettingsPage() {
  return (
    <AppShell title="Settings">
      <div className="page-container">
        <div className="page-header">
          <div>
            <h1 className="page-title">Settings</h1>
            <p className="page-subtitle">Manage your account and preferences.</p>
          </div>
        </div>

        <Tabs
          items={[
            {
              id: "profile",
              label: "Profile",
              icon: <User size={14} />,
              content: <ProfileTab />,
            },
            {
              id: "notifications",
              label: "Notifications",
              icon: <Bell size={14} />,
              content: <NotificationsTab />,
            },
            {
              id: "security",
              label: "Security",
              icon: <Shield size={14} />,
              content: <SecurityTab />,
            },
          ]}
          defaultTab="profile"
        />
      </div>
    </AppShell>
  );
}
