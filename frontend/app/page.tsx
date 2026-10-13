"use client";

import React, { useEffect, useState } from "react";
import {
  AuthStatus,
  DocumentMetadata,
  AnalysisResponse,
  fetchAuthStatus,
  fetchRecentDocuments,
  analyzeDocument,
} from "../lib/api";
import ConnectDrive from "../components/ConnectDrive";
import ReadOnlyNotice from "../components/ReadOnlyNotice";
import DocumentSummary from "../components/DocumentSummary";
import {
  Sparkles,
  Layers,
  FileText,
  AlertTriangle,
  RefreshCw,
  Clock,
  CheckCircle2,
  ExternalLink,
  ShieldAlert,
} from "lucide-react";

export default function HomePage() {
  const [authStatus, setAuthStatus] = useState<AuthStatus | null>(null);
  const [loadingAuth, setLoadingAuth] = useState(true);
  const [documents, setDocuments] = useState<DocumentMetadata[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);

  // Check auth status on load
  const loadAuth = async () => {
    try {
      setLoadingAuth(true);
      const status = await fetchAuthStatus();
      setAuthStatus(status);
      if (status.is_authenticated) {
        loadRecentDocuments();
      } else {
        setDocuments([]);
        setAnalysisResult(null);
      }
    } catch (err: any) {
      console.error("Auth check failed:", err);
      setAuthStatus({ is_authenticated: false, read_only_enforced: true });
    } finally {
      setLoadingAuth(false);
    }
  };

  const loadRecentDocuments = async () => {
    try {
      setLoadingDocs(true);
      setErrorMessage(null);
      const docs = await fetchRecentDocuments();
      setDocuments(docs);
    } catch (err: any) {
      console.error("Failed to load documents:", err);
      setErrorMessage(err.message || "Failed to load recent files from Google Drive.");
    } finally {
      setLoadingDocs(false);
    }
  };

  useEffect(() => {
    // Check URL parameters for auth redirects
    if (typeof window !== "undefined") {
      const urlParams = new URLSearchParams(window.location.search);
      const authErr = urlParams.get("auth_error");
      if (authErr) {
        setErrorMessage(`Google Authorization Error: ${authErr}`);
        // Clean URL
        window.history.replaceState({}, document.title, window.location.pathname);
      }
      const authSuccess = urlParams.get("auth");
      if (authSuccess) {
        window.history.replaceState({}, document.title, window.location.pathname);
      }
    }
    loadAuth();
  }, []);

  const handleAnalyze = async (docId?: string) => {
    try {
      setAnalyzing(true);
      setErrorMessage(null);
      setAnalysisResult(null);
      const targetId = docId || selectedDocId || undefined;
      const result = await analyzeDocument(targetId);
      setAnalysisResult(result);
    } catch (err: any) {
      console.error("Analysis error:", err);
      setErrorMessage(err.message || "Analysis request failed.");
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <main className="max-w-5xl mx-auto px-4 py-10 space-y-8">
      {/* Header Banner */}
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-6 pb-6 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-extrabold tracking-tight text-white">
                DriveLens <span className="text-cyan-400">AI</span>
              </h1>
              <p className="text-sm text-slate-400">
                Read-Only Document Intelligence Assistant
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
            <span>API Scope: <strong>drive.readonly</strong></span>
          </div>
        </div>
      </header>

      {/* Security Architecture & Least-Privilege Notice */}
      <ReadOnlyNotice />

      {/* Connect Google Drive Status Card */}
      <ConnectDrive
        authStatus={authStatus}
        onStatusChange={loadAuth}
        isLoading={loadingAuth}
      />

      {/* Main Analysis Action Section */}
      {authStatus?.is_authenticated && (
        <section className="space-y-6">
          <div className="card-glass p-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Layers className="w-5 h-5 text-cyan-400" />
                  Analyze Latest Document
                </h3>
                <p className="text-sm text-slate-300 mt-0.5">
                  Retrieves the most recently modified eligible document from your Drive and extracts 3 facts plus a summary.
                </p>
              </div>

              <div className="flex items-center gap-3 w-full sm:w-auto">
                <button
                  onClick={() => loadRecentDocuments()}
                  disabled={loadingDocs}
                  className="btn-secondary inline-flex items-center justify-center gap-1.5"
                  title="Refresh list of files from Drive"
                >
                  <RefreshCw className={`w-4 h-4 ${loadingDocs ? "animate-spin-fast" : ""}`} />
                  <span>Refresh</span>
                </button>

                <button
                  onClick={() => handleAnalyze()}
                  disabled={analyzing}
                  className="btn-primary w-full sm:w-auto inline-flex items-center justify-center gap-2"
                >
                  {analyzing ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin-fast" />
                      <span>Extracting & Analyzing...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      <span>{selectedDocId ? "Analyze Selected File" : "Analyze Most Recent File"}</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* List of Recent Files in User's Drive */}
            {documents.length > 0 && (
              <div className="mt-6 pt-5 border-t border-slate-800">
                <div className="flex items-center justify-between mb-3 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  <span>Recent Files in Authorized Account ({documents.length})</span>
                  <span>Click to select specific document</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 max-h-56 overflow-y-auto pr-1">
                  {documents.map((doc, idx) => {
                    const isSelected = selectedDocId === doc.id || (!selectedDocId && idx === 0);
                    return (
                      <div
                        key={doc.id}
                        onClick={() => {
                          if (doc.is_supported) setSelectedDocId(doc.id);
                        }}
                        className={`p-3 rounded-lg border text-left cursor-pointer transition-all ${
                          isSelected
                            ? "bg-cyan-950/40 border-cyan-500/60 shadow-md shadow-cyan-950/20"
                            : "bg-slate-900/40 border-slate-800 hover:border-slate-700"
                        } ${!doc.is_supported ? "opacity-60 cursor-not-allowed" : ""}`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex items-center gap-2 min-w-0">
                            <FileText className={`w-4 h-4 shrink-0 ${isSelected ? "text-cyan-400" : "text-slate-400"}`} />
                            <span className="text-sm font-medium text-white truncate">{doc.name}</span>
                          </div>
                          {idx === 0 && (
                            <span className="text-[10px] uppercase font-bold bg-indigo-500/20 text-indigo-300 px-1.5 py-0.5 rounded shrink-0">
                              Latest
                            </span>
                          )}
                        </div>

                        <div className="flex items-center justify-between mt-2 text-[11px] text-slate-400">
                          <span className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {new Date(doc.modified_time).toLocaleDateString()}
                          </span>
                          <span>
                            {doc.is_supported ? (
                              <span className="text-emerald-400">Supported</span>
                            ) : (
                              <span className="text-amber-400" title={doc.unsupported_reason || "Unsupported"}>
                                Unsupported
                              </span>
                            )}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Analysis In-Progress State */}
          {analyzing && (
            <div className="card-glass p-8 text-center space-y-4">
              <div className="w-12 h-12 rounded-full border-2 border-cyan-500 border-t-transparent animate-spin-fast mx-auto" />
              <div>
                <h4 className="text-lg font-bold text-white">Analyzing Document Content</h4>
                <p className="text-sm text-slate-300 mt-1 max-w-md mx-auto">
                  Fetching document bytes via Google Drive read-only API, extracting clean text, and generating evidence-grounded facts using OpenAI...
                </p>
              </div>
            </div>
          )}

          {/* Analysis Results View */}
          {analysisResult && !analyzing && (
            <DocumentSummary analysis={analysisResult} />
          )}
        </section>
      )}

      {/* Error Alert Display */}
      {errorMessage && (
        <div className="p-4 rounded-xl bg-rose-950/60 border border-rose-800 text-rose-200 flex items-start gap-3">
          <ShieldAlert className="w-5 h-5 shrink-0 text-rose-400 mt-0.5" />
          <div className="text-sm space-y-1">
            <h4 className="font-semibold text-white">Application Alert</h4>
            <p>{errorMessage}</p>
          </div>
        </div>
      )}

      {/* Information Banner for Educational Transparency */}
      <footer className="text-xs text-slate-400 border-t border-slate-800/80 pt-6 space-y-2">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <p>
            <strong>DriveLens AI</strong> &mdash; Production-Minded Educational Architecture. No manual uploads required.
          </p>
          <div className="flex items-center gap-4 text-cyan-400">
            <a
              href="https://developers.google.com/drive/api/guides/api-specific-auth"
              target="_blank"
              rel="noreferrer"
              className="hover:underline flex items-center gap-1"
            >
              Google Drive API Scopes <ExternalLink className="w-3 h-3" />
            </a>
            <a
              href="https://platform.openai.com/docs/guides/structured-outputs"
              target="_blank"
              rel="noreferrer"
              className="hover:underline flex items-center gap-1"
            >
              OpenAI Structured Outputs <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>
      </footer>
    </main>
  );
}
