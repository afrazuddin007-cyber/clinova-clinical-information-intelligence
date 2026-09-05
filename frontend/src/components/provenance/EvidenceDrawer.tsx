import React, { useEffect } from 'react';
import { ExtractedLabResult } from '../../types';
import { reportApi } from '../../services/api';
import { RangeStatusBadge } from '../common/RangeStatusBadge';
import { ProvenanceBadge } from '../common/ProvenanceBadge';
import {
  X,
  FileText,
  ExternalLink,
  ShieldCheck,
  Clock,
  Sparkles,
  Quote,
  Layers,
  AlertCircle,
  FileSearch
} from 'lucide-react';

interface EvidenceDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  lab: ExtractedLabResult | null;
}

export const EvidenceDrawer: React.FC<EvidenceDrawerProps> = ({
  isOpen,
  onClose,
  lab,
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  // Fallback if lab is absent
  if (!lab) {
    return (
      <div className="fixed inset-0 z-50 overflow-hidden">
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs transition-opacity" onClick={onClose} />
        <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
          <div className="w-screen max-w-xl bg-white shadow-2xl border-l border-slate-200 flex flex-col p-6">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-sm font-bold text-slate-900">Source Evidence</h3>
              <button onClick={onClose} className="p-1 rounded text-slate-400 hover:text-slate-600"><X className="w-4 h-4" /></button>
            </div>
            <div className="p-6 bg-slate-50 rounded-xl border border-slate-200 text-center text-slate-500 text-xs">
              Not found in the verified records.
            </div>
          </div>
        </div>
      </div>
    );
  }

  const fileUrl = lab.report_id ? reportApi.getFileUrl(lab.report_id) : null;
  const hasSnippet = Boolean(lab.source_snippet && lab.source_snippet.trim());

  return (
    <div className="fixed inset-0 z-50 overflow-hidden" role="dialog" aria-modal="true" aria-labelledby="evidence-drawer-title">
      {/* Dimmed Backdrop */}
      <div
        className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs transition-opacity animate-in fade-in"
        onClick={onClose}
      />

      <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-xl bg-white shadow-2xl border-l border-slate-200 flex flex-col animate-in slide-in-from-right duration-250 ease-out">
          {/* Drawer Header */}
          <div className="p-4 sm:p-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
            <div>
              <div className="flex items-center gap-2">
                <FileSearch className="w-4 h-4 text-sky-600" />
                <h3 id="evidence-drawer-title" className="text-sm font-bold text-slate-900">
                  Source Provenance & Evidence Trace
                </h3>
              </div>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Exact documented parameters linked directly to source report
              </p>
            </div>

            <button
              type="button"
              onClick={onClose}
              aria-label="Close evidence drawer"
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-slate-300"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Drawer Body */}
          <div className="flex-1 overflow-y-auto p-5 space-y-6 text-xs">
            {/* 1. Clinical Parameter Overview Card */}
            <div className="bg-slate-50/80 p-4 rounded-xl border border-slate-200/90 space-y-3 shadow-2xs">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                  Documented Finding
                </span>
                <ProvenanceBadge
                  provenance={lab.provenance_type}
                  verificationStatus={lab.verification_status}
                />
              </div>

              <div className="flex items-baseline justify-between gap-4">
                <div className="text-base font-bold text-slate-900">{lab.test_name}</div>
                <div className="text-right">
                  <span className="font-mono text-lg font-bold text-slate-900">
                    {lab.raw_value}
                  </span>
                  {lab.unit && (
                    <span className="ml-1 font-mono text-xs text-slate-600 font-semibold">{lab.unit}</span>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 pt-2.5 border-t border-slate-200/70 text-[11px]">
                <div>
                  <span className="text-slate-500 block mb-0.5">Printed Reference Range</span>
                  <span className="font-mono font-semibold text-slate-800">
                    {lab.raw_reference_range || (
                      <span className="text-slate-400 italic">None printed on report</span>
                    )}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block mb-0.5">Clinova Deterministic Status</span>
                  <div className="mt-0.5">
                    <RangeStatusBadge status={lab.range_status} />
                  </div>
                </div>
              </div>
            </div>

            {/* 2. Verbatim Source Evidence Snippet */}
            <div className="space-y-2">
              <div className="flex items-center gap-1.5 text-slate-700 font-semibold">
                <Quote className="w-3.5 h-3.5 text-slate-500" />
                <span>Verbatim Source Evidence Snippet</span>
              </div>

              {hasSnippet ? (
                <div className="p-4 bg-slate-900 text-slate-100 rounded-xl font-mono text-xs leading-relaxed border border-slate-800 shadow-inner">
                  "{lab.source_snippet}"
                </div>
              ) : (
                <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 text-slate-500 italic text-xs">
                  Not found in the verified records.
                </div>
              )}

              <p className="text-[10px] text-slate-400">
                Clinova strictly references explicitly recorded text. Never infers or assumes unstated facts.
              </p>
            </div>

            {/* 3. Source Document Reference & Page Location */}
            <div className="space-y-2.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-slate-700 font-semibold">
                  <FileText className="w-3.5 h-3.5 text-slate-500" />
                  <span>Original Document Reference</span>
                </div>

                {fileUrl && (
                  <a
                    href={fileUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-[11px] font-semibold text-sky-600 hover:text-sky-800 hover:underline"
                  >
                    <ExternalLink className="w-3 h-3" />
                    Open Source File
                  </a>
                )}
              </div>

              <div className="p-3.5 bg-slate-50/80 rounded-xl border border-slate-200/90 flex items-center justify-between">
                <div>
                  <div className="font-semibold text-slate-800">
                    {lab.report_file_name || 'Source_Medical_Report.pdf'}
                  </div>
                  <div className="text-[11px] text-slate-500 mt-0.5">
                    Source Page: <strong className="text-slate-800 font-mono">Page {lab.page_number || 1}</strong>
                  </div>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-200 text-slate-700">
                  ID: {lab.report_id?.slice(0, 8)}...
                </span>
              </div>

              {/* Embedded Document Viewer Preview */}
              {fileUrl && (
                <div className="rounded-xl border border-slate-200/90 overflow-hidden bg-slate-100 h-64 relative">
                  <iframe
                    src={`${fileUrl}#page=${lab.page_number || 1}`}
                    title="Source Document Preview"
                    className="w-full h-full border-0"
                  />
                </div>
              )}
            </div>

            {/* 4. Verification & Audit Integrity Card */}
            <div className="space-y-2 pt-2 border-t border-slate-100">
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                Verification & Audit Integrity
              </span>

              <div className="p-3.5 rounded-xl border border-slate-200 bg-white space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Verification Lifecycle</span>
                  <span className="font-semibold text-slate-900">
                    {lab.verification_status === 'HUMAN_VERIFIED' ? 'Verified by Clinician' : 'Pending Review'}
                  </span>
                </div>

                {lab.verified_at && (
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-slate-500">Verified Timestamp</span>
                    <span className="font-mono text-slate-700">
                      {new Date(lab.verified_at).toLocaleString()}
                    </span>
                  </div>
                )}

                {lab.original_ai_value && (
                  <div className="pt-2 border-t border-slate-100 text-[11px]">
                    <span className="text-slate-500 block">Original Extracted Value (Audited):</span>
                    <span className="font-mono text-slate-700 font-medium">
                      {lab.original_ai_value}
                    </span>
                    {lab.human_override_notes && (
                      <p className="text-slate-600 mt-1 italic">
                        Clinician rationale: "{lab.human_override_notes}"
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Drawer Footer */}
          <div className="p-4 border-t border-slate-100 bg-slate-50/50 flex items-center justify-between">
            <span className="text-[11px] text-slate-400 flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
              Traceable Record Grounding
            </span>
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-1.5 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 rounded-lg shadow-2xs transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-slate-300"
            >
              Done
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
