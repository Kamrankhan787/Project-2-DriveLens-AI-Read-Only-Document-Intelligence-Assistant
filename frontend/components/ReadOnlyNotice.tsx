"use client";

import React, { useState } from "react";
import { ShieldCheck, Lock, ExternalLink, ChevronDown, ChevronUp, AlertCircle } from "lucide-react";

export default function ReadOnlyNotice() {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="security-notice-card">
      <div className="security-notice-header">
        <div className="security-badge-icon">
          <ShieldCheck className="w-5 h-5 text-emerald-400" />
        </div>
        <div className="security-title-group">
          <div className="flex items-center gap-2">
            <h3 className="security-headline">Strict Read-Only Architecture</h3>
            <span className="badge-verified">OAuth Least-Privilege</span>
          </div>
          <p className="security-subtitle">
            DriveLens AI is architecturally restricted from modifying, creating, or deleting your Google Drive files.
          </p>
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="security-toggle-btn"
          aria-expanded={expanded}
          aria-label="Toggle technical proof details"
        >
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          <span>{expanded ? "Hide Details" : "Why Read-Only?"}</span>
        </button>
      </div>

      {expanded && (
        <div className="security-expanded-content">
          <div className="security-grid">
            <div className="security-col allowed">
              <h4>
                <ShieldCheck className="w-4 h-4 text-emerald-400 inline mr-1" />
                What DriveLens AI Can Do:
              </h4>
              <ul>
                <li>Request list of recent documents to identify the latest file.</li>
                <li>Read metadata (document name, MIME type, last modified date).</li>
                <li>Export Google Docs text or read text formats (PDF, TXT, DOCX) for summarization.</li>
                <li>Process text through OpenAI for structured 3-fact extraction.</li>
              </ul>
            </div>

            <div className="security-col forbidden">
              <h4>
                <Lock className="w-4 h-4 text-rose-400 inline mr-1" />
                What DriveLens AI Cannot Do:
              </h4>
              <ul>
                <li><strong>No file creation:</strong> Cannot upload or create files or folders.</li>
                <li><strong>No file modification:</strong> Zero endpoints exist to edit or patch content.</li>
                <li><strong>No file deletion:</strong> Cannot trash, delete, or wipe documents.</li>
                <li><strong>No sharing alterations:</strong> Cannot change permissions or share files.</li>
              </ul>
            </div>
          </div>

          <div className="security-footer-info">
            <div className="flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-cyan-400 mt-0.5 shrink-0" />
              <div className="text-xs text-slate-300 space-y-1">
                <p>
                  <strong>Why Write Access Is Unnecessary:</strong> A document intelligence assistant is strictly an observer.
                  Granting write scopes (<code>drive</code> or <code>drive.file</code>) would violate the principle of least privilege.
                  Read-only access is enforced by Google's OAuth consent scope: <code>https://www.googleapis.com/auth/drive.readonly</code>.
                </p>
                <p>
                  <strong>Revocation at Any Time:</strong> You can disconnect here or revoke access immediately via your{" "}
                  <a
                    href="https://myaccount.google.com/permissions"
                    target="_blank"
                    rel="noreferrer"
                    className="text-cyan-400 underline hover:text-cyan-300 inline-flex items-center gap-1"
                  >
                    Google Account Permissions
                    <ExternalLink className="w-3 h-3" />
                  </a>.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
