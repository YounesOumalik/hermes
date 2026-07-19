"use client";

import { Shield, Key } from "lucide-react";
import { Card, Button } from "@/components/ui";

/**
 * Onglet Security : placeholder pour futur changement de mot de passe + 2FA + sessions.
 * Pas encore d'endpoint backend correspondant.
 */
export function SecurityTab() {
  return (
    <div className="settings-section">
      <div className="settings-section-header">
        <Shield size={16} />
        <h3 className="settings-section-title">Security</h3>
      </div>

      <Card variant="flat" padding="md">
        <div className="security-item">
          <div className="security-info">
            <div className="security-label-row">
              <Key size={14} />
              <h4 className="security-label">Password</h4>
            </div>
            <p className="security-description">
              Change your account password. (Coming soon)
            </p>
          </div>
          <Button variant="secondary" size="sm" disabled>
            Change
          </Button>
        </div>
      </Card>

      <Card variant="flat" padding="md">
        <div className="security-item">
          <div className="security-info">
            <div className="security-label-row">
              <Shield size={14} />
              <h4 className="security-label">Two-factor authentication</h4>
            </div>
            <p className="security-description">
              Add an extra layer of security with TOTP. (Coming soon)
            </p>
          </div>
          <Button variant="secondary" size="sm" disabled>
            Enable
          </Button>
        </div>
      </Card>

      <Card variant="flat" padding="md">
        <div className="security-item">
          <div className="security-info">
            <div className="security-label-row">
              <Shield size={14} />
              <h4 className="security-label">Active sessions</h4>
            </div>
            <p className="security-description">
              Sign out from other devices. (Coming soon)
            </p>
          </div>
          <Button variant="secondary" size="sm" disabled>
            View
          </Button>
        </div>
      </Card>
    </div>
  );
}

export default SecurityTab;
