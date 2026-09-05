import React from 'react';
import { ExtractedLabResult, MedicalReport } from '../../types';
import { ProvenanceBadge } from '../common/ProvenanceBadge';
import { RangeStatusBadge } from '../common/RangeStatusBadge';
import { X, FileText, Calendar, CheckCircle, ExternalLink, Quote, Shield } from 'lucide-react';
import { reportApi } from '../../services/api';

interface ProvenanceInspectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  targetLab: ExtractedLabResult | null;
  report?: MedicalReport | null;
}

export const ProvenanceInspectorModal: React.FC<ProvenanceInspectorModalProps> = ({
  isOpen,
  onClose,
  targetLab,
  report,
}) => {
  if (!isOpen || !targetLab) return null;

  const fileUrl = reportApi.getFileUrl(targetLab.report_id);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/70 backdrop-blur-xs">
      <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-4xl w-full max-h-[92vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95">
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-slate-200 flex items-center justify-between bg-slate-900 text-white">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-sky-500/20 text-sky-400 flex items-center justify-center border border-sky-400/30">
              <Shield className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold tracking-tight">Source Evidence & Provenance Inspector</h3>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-sky-500/30 text-sky-200">
                  Traceable Audit Chain
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Verifiable origin evidence for: <strong className="text-white">{targetLab.test_name}</strong>
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-white/10"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Two-Column Inspector Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 flex-1 overflow-hidden">
          {/* Left Column: Metadata & Verbatim Snippet */}
          <div className="lg:col-span-5 p-5 border-r border-slate-200 bg-slate-50/50 overflow-y-auto space-y-4 text-xs">
            {/* Finding Overview */}
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-2">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                Structured Clinical Extraction
              </span>
              <div className="flex items-center justify-between">
                <span className="text-sm font-bold text-slate-900">{targetLab.test_name}</span>
                <RangeStatusBadge status={targetLab.range_status} />
              </div>

              <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-100 font-mono">
                <div>
                  <span className="text-[10px] text-slate-400 block font-sans">Recorded Value:</span>
                  <span className="text-base font-bold text-slate-900">{targetLab.raw_value} {targetLab.unit || ''}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 block font-sans">Reference Range:</span>
                  <span className="text-xs text-slate-700">{targetLab.raw_reference_range || 'None provided'}</span>
                </div>
              </div>
            </div>

            {/* Verbatim Source Evidence Snippet */}
            <div className="bg-white p-4 rounded-xl border border-sky-200 shadow-xs">
              <span className="text-[10px] font-bold text-sky-800 uppercase tracking-wider flex items-center gap-1 mb-2">
                <Quote className="w-3.5 h-3.5 text-sky-600" />
                Verbatim Document Snippet
              </span>
              <div className="bg-sky-50/70 p-3 rounded-lg border border-sky-100 text-slate-800 font-mono text-xs leading-relaxed">
                "{targetLab.source_snippet || 'Document text extracted during optical parsing.'}"
              </div>
              <p className="text-[11px] text-slate-500 mt-2">
                Captured on <strong>Page {targetLab.page_number}</strong> of the original document.
              </p>
            </div>

            {/* Audit & Provenance Metadata */}
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-2.5">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                Provenance Chain
              </span>

              <div className="flex items-center justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Origin Type:</span>
                <ProvenanceBadge provenance={targetLab.provenance_type} />
              </div>

              <div className="flex items-center justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Verification State:</span>
                <span className={`font-semibold ${targetLab.verification_status === 'HUMAN_VERIFIED' ? 'text-emerald-700' : 'text-amber-700'}`}>
                  {targetLab.verification_status}
                </span>
              </div>

              <div className="flex items-center justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Extracted Timestamp:</span>
                <span className="font-mono text-slate-700">
                  {new Date(targetLab.created_at).toLocaleString()}
                </span>
              </div>

              {targetLab.human_override_notes && (
                <div className="pt-2">
                  <span className="text-slate-500 block mb-1 font-semibold">Clinician Edit Notes:</span>
                  <div className="p-2 rounded bg-emerald-50 text-emerald-800 text-[11px] border border-emerald-200">
                    {targetLab.human_override_notes}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Source Document Viewer */}
          <div className="lg:col-span-7 flex flex-col bg-slate-900 overflow-hidden">
            <div className="p-2.5 bg-slate-800 text-slate-300 text-xs flex items-center justify-between px-4">
              <span className="flex items-center gap-1.5 truncate">
                <FileText className="w-3.5 h-3.5 text-sky-400" />
                {targetLab.report_file_name || 'Original Medical Report'} (Page {targetLab.page_number})
              </span>
              <a
                href={fileUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-[11px] text-sky-400 hover:text-sky-300 underline"
              >
                <ExternalLink className="w-3 h-3" />
                Open In New Tab
              </a>
            </div>

            <div className="flex-1 p-2 bg-slate-950 flex items-center justify-center overflow-hidden">
              <iframe
                src={`${fileUrl}#page=${targetLab.page_number}`}
                title="Original Medical Report Viewer"
                className="w-full h-full border-0 rounded-lg bg-white"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
