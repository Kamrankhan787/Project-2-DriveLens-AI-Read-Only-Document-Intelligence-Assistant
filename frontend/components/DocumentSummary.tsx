"use client";

import React, { useState } from "react";
import { AnalysisResponse } from "../lib/api";
import {
  FileText,
  Calendar,
  Sparkles,
  CheckCircle,
  Quote,
  AlertCircle,
  ShieldCheck,
  Hash,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

interface DocumentSummaryProps {
  analysis: AnalysisResponse;
}

export default function DocumentSummary({ analysis }: DocumentSummaryProps) {
  const [showEvidence, setShowEvidence] = useState(true);

  // Format timestamp nicely
  const formatDate = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        timeZoneName: "short",
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="space-y-6">
      {/* Document Source Verification Card */}
      <div className="card-glass p-6 border-l-4 border-l-cyan-500">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-cyan-400">
              <FileText className="w-4 h-4" />
              <span>Verified Source Document</span>
            </div>
            <h2 className="text-2xl font-bold text-white mt-1 tracking-tight">
              {analysis.document_title}
            </h2>
            <div className="flex flex-wrap items-center gap-4 mt-2 text-xs text-slate-400">
              <div className="flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5 text-slate-400" />
                <span>Last Modified: {formatDate(analysis.last_modified)}</span>
              </div>
              <span className="bg-slate-800 text-slate-300 px-2 py-0.5 rounded font-mono">
                {analysis.mime_type}
              </span>
              <span className="flex items-center gap-1 text-emerald-400 font-medium">
                <ShieldCheck className="w-3.5 h-3.5" />
                Read-Only Fetch
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* One-Line Summary Hero Box */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-indigo-950/70 via-slate-900 to-cyan-950/70 border border-indigo-700/40 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 translate-x-4 -translate-y-4 w-32 h-32 bg-cyan-500/10 rounded-full blur-2xl pointer-events-none" />
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-xl bg-indigo-500/20 text-cyan-300 shrink-0">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-indigo-300">
              Executive One-Line Summary
            </h3>
            <p className="text-lg md:text-xl font-medium text-white mt-1 leading-snug">
              {analysis.one_line_summary}
            </p>
          </div>
        </div>
      </div>

      {/* Exactly Three Key Facts & Numbers */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-base font-semibold text-white flex items-center gap-2">
            <Hash className="w-4 h-4 text-cyan-400" />
            Top 3 Evidence-Based Facts & Numbers
          </h3>
          <span className="text-xs text-slate-400">Grounded exclusively in source text</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {analysis.key_facts.map((fact, index) => {
            const isShortage = fact.toLowerCase().includes("shortage");

            return (
              <div
                key={index}
                className={`p-5 rounded-xl border transition-all duration-200 flex flex-col justify-between ${
                  isShortage
                    ? "bg-amber-950/20 border-amber-800/40 text-amber-200"
                    : "bg-slate-900/60 border-slate-800 hover:border-slate-700 hover:bg-slate-900/80 text-slate-200"
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span
                      className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                        isShortage
                          ? "bg-amber-500/20 text-amber-300"
                          : "bg-cyan-500/20 text-cyan-300"
                      }`}
                    >
                      Fact {index + 1}
                    </span>
                    {!isShortage && <CheckCircle className="w-4 h-4 text-cyan-400" />}
                  </div>
                  <p className="text-sm font-medium leading-relaxed">{fact}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Source Evidence & Citations */}
      {analysis.source_evidence && analysis.source_evidence.length > 0 && (
        <div className="card-glass p-5">
          <button
            onClick={() => setShowEvidence(!showEvidence)}
            className="w-full flex items-center justify-between text-left"
          >
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
              <Quote className="w-4 h-4 text-cyan-400" />
              <span>Direct Quotations & Source Evidence</span>
            </div>
            {showEvidence ? (
              <ChevronUp className="w-4 h-4 text-slate-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-slate-400" />
            )}
          </button>

          {showEvidence && (
            <div className="mt-4 space-y-2.5">
              {analysis.source_evidence.map((quote, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 text-xs font-mono text-cyan-200/90 leading-relaxed"
                >
                  "{quote}"
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Document Limitations & Data Gaps */}
      {analysis.limitations && analysis.limitations.length > 0 && (
        <div className="p-4 rounded-xl bg-slate-950/40 border border-slate-800/80 flex items-start gap-3">
          <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div className="text-xs text-slate-400 space-y-1">
            <span className="font-semibold text-slate-300 uppercase tracking-wide">
              Document Scope & Identified Limitations:
            </span>
            <ul className="list-disc list-inside space-y-1 pl-1">
              {analysis.limitations.map((limit, idx) => (
                <li key={idx}>{limit}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Read-Only Guarantee Footer */}
      <div className="text-center text-xs text-slate-500 pt-2">
        <ShieldCheck className="w-3.5 h-3.5 inline mr-1 text-emerald-500" />
        {analysis.read_only_notice}
      </div>
    </div>
  );
}
