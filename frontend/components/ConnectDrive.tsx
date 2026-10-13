"use client";

import React, { useState } from "react";
import { AuthStatus, getGoogleLoginUrl, disconnectDrive } from "../lib/api";
import { LogIn, LogOut, CheckCircle2, AlertTriangle, ShieldCheck, RefreshCw } from "lucide-react";

interface ConnectDriveProps {
  authStatus: AuthStatus | null;
  onStatusChange: () => void;
  isLoading: boolean;
}

export default function ConnectDrive({ authStatus, onStatusChange, isLoading }: ConnectDriveProps) {
  const [disconnecting, setDisconnecting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleConnect = () => {
    // Redirect browser to backend Google OAuth login route
    window.location.href = getGoogleLoginUrl();
  };

  const handleDisconnect = async () => {
    try {
      setDisconnecting(true);
      setErrorMsg(null);
      await disconnectDrive();
      onStatusChange();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to disconnect");
    } finally {
      setDisconnecting(false);
    }
  };

  const isConnected = authStatus?.is_authenticated;

  return (
    <div className="card-glass p-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className={`status-indicator-dot ${isConnected ? "bg-emerald-400" : "bg-amber-400"}`} />
            <h2 className="text-xl font-bold tracking-tight text-white">
              {isConnected ? "Google Drive Connected" : "Connect Google Drive"}
            </h2>
          </div>
          <p className="text-sm text-slate-300 mt-1">
            {isConnected ? (
              <span>
                Authorized as <strong className="text-white font-medium">{authStatus.user_email || "Active User"}</strong>.
                Scope: <code className="text-xs bg-slate-800 px-1.5 py-0.5 rounded text-cyan-300">drive.readonly</code>
              </span>
            ) : (
              "Authorize DriveLens AI to read your most recent document via Google's secure OAuth 2.0 flow."
            )}
          </p>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          {isConnected ? (
            <button
              onClick={handleDisconnect}
              disabled={disconnecting}
              className="btn-danger w-full sm:w-auto inline-flex items-center justify-center gap-2"
            >
              <LogOut className="w-4 h-4" />
              <span>{disconnecting ? "Disconnecting..." : "Disconnect Drive"}</span>
            </button>
          ) : (
            <button
              onClick={handleConnect}
              disabled={isLoading}
              className="btn-primary w-full sm:w-auto inline-flex items-center justify-center gap-2"
            >
              <LogIn className="w-4 h-4" />
              <span>Connect Google Drive</span>
            </button>
          )}
        </div>
      </div>

      {errorMsg && (
        <div className="mt-4 p-3 rounded-lg bg-rose-950/50 border border-rose-800/60 flex items-center gap-2 text-sm text-rose-300">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}
    </div>
  );
}
