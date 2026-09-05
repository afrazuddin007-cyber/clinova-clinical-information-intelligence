import React, { useState } from 'react';
import { Patient, MedicalReport, ExtractedLabResult } from '../../types';
import { reportApi } from '../../services/api';
import { RangeStatusBadge } from '../common/RangeStatusBadge';
import { ProvenanceBadge } from '../common/ProvenanceBadge';
import {
  FileText,
  UploadCloud,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  GitCompare,
  CheckCircle2,
  AlertCircle,
  Building2,
  Calendar,
  Layers,
  Search
} from 'lucide-react';

interface PatientRecordsTabProps {
  patient: Patient;
  reports: MedicalReport[];
  labs: ExtractedLabResult[];
  onUploadClick: () => void;
  onCompareClick: (reportAId: string, reportBId: string) => void;
  onInspectProvenance: (lab: ExtractedLabResult) => void;
}

export const PatientRecordsTab: React.FC<PatientRecordsTabProps> = ({
  patient,
  reports,
  labs,
  onUploadClick,
  onCompareClick,
  onInspectProvenance,
}) => {
  const [expandedReportId, setExpandedReportId] = useState<string | null>(
    reports.length > 0 ? reports[0].id : null
  );
  const [searchQuery, setSearchQuery] = useState('');

  const toggleExpand = (id: string) => {
    setExpandedReportId((prev) => (prev === id ? null : id));
  };

  const filteredReports = reports.filter((r) => {
    const q = searchQuery.toLowerCase();
    return (
      r.original_file_name.toLowerCase().includes(q) ||
      (r.report_title && r.report_title.toLowerCase().includes(q)) ||
      (r.facility_name && r.facility_name.toLowerCase().includes(q))
    );
  });

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  if (reports.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-200/90 shadow-2xs p-12 text-center max-w-xl mx-auto">
        <div className="w-12 h-12 rounded-xl bg-slate-100 text-slate-400 flex items-center justify-center mx-auto mb-3">
          <FileText className="w-6 h-6" />
        </div>
        <h3 className="text-sm font-bold text-slate-800 mb-1">No Preserved Medical Records</h3>
        <p className="text-xs text-slate-500 mb-5">
          Upload PDF laboratory reports or diagnostic documents to initiate structured parsing, reference-range validation, and automated evidence tagging.
        </p>
        <button
          type="button"
          onClick={onUploadClick}
          className="inline-flex items-center gap-2 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-lg shadow-xs transition-colors cursor-pointer"
        >
          <UploadCloud className="w-4 h-4" />
          Upload First Medical Record
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4 max-w-5xl mx-auto">
      {/* Tab Sub-Header with search & upload CTA */}
      <div className="bg-white p-4 rounded-xl border border-slate-200/90 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-bold text-slate-900">
            Preserved Medical Records ({reports.length})
          </h2>
          <p className="text-[11px] text-slate-500">
            Chronological archive of source medical reports with structured parameter extraction
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search records..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-300 w-44"
            />
          </div>

          <button
            type="button"
            onClick={onUploadClick}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg shadow-2xs transition-colors cursor-pointer whitespace-nowrap"
          >
            <UploadCloud className="w-3.5 h-3.5" />
            Upload Record
          </button>
        </div>
      </div>

      {/* Reports List */}
      <div className="space-y-3">
        {filteredReports.map((report) => {
          const reportLabs = labs.filter((l) => l.report_id === report.id);
          const isExpanded = expandedReportId === report.id;
          const pendingCount = reportLabs.filter((l) => l.verification_status === 'PENDING_VERIFICATION').length;

          return (
            <div
              key={report.id}
              className="bg-white rounded-xl border border-slate-200/90 shadow-2xs overflow-hidden transition-all"
            >
              {/* Report Header Card */}
              <div
                className={`p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 cursor-pointer select-none transition-colors ${
                  isExpanded ? 'bg-slate-50/70 border-b border-slate-200/80' : 'hover:bg-slate-50/40'
                }`}
                onClick={() => toggleExpand(report.id)}
              >
                <div className="flex items-start gap-3">
                  <button
                    type="button"
                    className="mt-0.5 text-slate-400 hover:text-slate-600 cursor-pointer"
                    aria-label={isExpanded ? 'Collapse' : 'Expand'}
                  >
                    {isExpanded ? (
                      <ChevronDown className="w-4 h-4" />
                    ) : (
                      <ChevronRight className="w-4 h-4" />
                    )}
                  </button>

                  <div className="w-9 h-9 rounded-lg bg-slate-100 text-slate-700 flex items-center justify-center shrink-0">
                    <FileText className="w-4 h-4" />
                  </div>

                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-bold text-slate-900">
                        {report.report_title || report.original_file_name}
                      </span>

                      <span
                        className={`text-[10px] font-semibold px-2 py-0.5 rounded ${
                          report.processing_status === 'EXTRACTED'
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200/80'
                            : report.processing_status === 'PROCESSING'
                            ? 'bg-sky-50 text-sky-700 border border-sky-200/80'
                            : 'bg-amber-50 text-amber-700 border border-amber-200/80'
                        }`}
                      >
                        {report.processing_status}
                      </span>

                      {pendingCount > 0 && (
                        <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-amber-100 text-amber-800">
                          {pendingCount} Pending Review
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-3 text-[11px] text-slate-400 mt-1 flex-wrap">
                      <span className="text-slate-500 font-mono text-[11px]">
                        {report.original_file_name}
                      </span>
                      <span>•</span>
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3 text-slate-400" />
                        {report.report_date
                          ? new Date(report.report_date).toLocaleDateString()
                          : new Date(report.uploaded_at).toLocaleDateString()}
                      </span>
                      {report.facility_name && (
                        <>
                          <span>•</span>
                          <span className="flex items-center gap-1">
                            <Building2 className="w-3 h-3 text-slate-400" />
                            {report.facility_name}
                          </span>
                        </>
                      )}
                      <span>•</span>
                      <span>{formatFileSize(report.file_size_bytes)}</span>
                      <span>•</span>
                      <span className="font-semibold text-slate-600">
                        {reportLabs.length} Finding{reportLabs.length !== 1 ? 's' : ''}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Card Top Actions */}
                <div
                  className="flex items-center gap-2 self-end sm:self-center"
                  onClick={(e) => e.stopPropagation()}
                >
                  {/* View Original Document */}
                  <a
                    href={reportApi.getFileUrl(report.id)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 rounded-md transition-colors shadow-2xs"
                    title="Open original preserved PDF or image"
                  >
                    <ExternalLink className="w-3 h-3 text-slate-400" />
                    Original File
                  </a>

                  {/* Compare Button if multiple reports exist */}
                  {reports.length > 1 && (
                    <button
                      type="button"
                      onClick={() => {
                        const otherReport = reports.find((r) => r.id !== report.id);
                        if (otherReport) {
                          onCompareClick(report.id, otherReport.id);
                        }
                      }}
                      className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 rounded-md transition-colors shadow-2xs cursor-pointer"
                      title="Compare this report with another"
                    >
                      <GitCompare className="w-3 h-3 text-slate-400" />
                      Compare
                    </button>
                  )}
                </div>
              </div>

              {/* Expandable Structured Extraction Table */}
              {isExpanded && (
                <div className="border-t border-slate-100 bg-white p-4 animate-in fade-in-50 duration-200">
                  <div className="mb-2.5 flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                      <Layers className="w-3.5 h-3.5 text-slate-500" />
                      Structured Extraction Findings ({reportLabs.length})
                    </span>
                    <span className="text-[10px] text-slate-400">
                      Evaluated deterministically against source-provided reference ranges
                    </span>
                  </div>

                  {reportLabs.length === 0 ? (
                    <div className="py-8 text-center text-xs text-slate-400">
                      No numerical laboratory parameters extracted from this document.
                    </div>
                  ) : (
                    <div className="overflow-x-auto max-h-[500px] overflow-y-auto rounded-xl border border-slate-200/90 shadow-2xs">
                      <table className="w-full text-left text-xs border-collapse">
                        <thead className="sticky top-0 z-10 bg-slate-50/95 backdrop-blur-xs border-b border-slate-200 text-[11px] text-slate-500 font-semibold uppercase tracking-wider">
                          <tr>
                            <th className="px-4 py-2.5">Test / Biomarker</th>
                            <th className="px-4 py-2.5">Measured Result</th>
                            <th className="px-4 py-2.5">Unit</th>
                            <th className="px-4 py-2.5">Source Reference Range</th>
                            <th className="px-4 py-2.5">Clinova Status</th>
                            <th className="px-4 py-2.5">Verification</th>
                            <th className="px-4 py-2.5 text-right">Evidence</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 font-normal bg-white">
                          {reportLabs.map((lab) => (
                            <tr key={lab.id} className="hover:bg-sky-50/30 focus-within:bg-sky-50/40 transition-colors group">
                              <td className="px-4 py-2.5 font-semibold text-slate-900">
                                <div>{lab.test_name}</div>
                                {lab.human_override_notes && (
                                  <span className="block text-[10px] text-emerald-600 font-normal italic mt-0.5">
                                    Edited: {lab.human_override_notes}
                                  </span>
                                )}
                              </td>
                              <td className="px-4 py-2.5 font-mono font-bold text-slate-900 text-sm">
                                {lab.raw_value}
                              </td>
                              <td className="px-4 py-2.5 text-slate-600 font-mono text-[11px]">
                                {lab.unit || '—'}
                              </td>
                              <td className="px-4 py-2.5 font-mono text-[11px] text-slate-700">
                                {lab.raw_reference_range || (
                                  <span className="text-slate-400 italic">None printed on report</span>
                                )}
                              </td>
                              <td className="px-4 py-2.5">
                                <RangeStatusBadge status={lab.range_status} />
                              </td>
                              <td className="px-4 py-2.5">
                                <ProvenanceBadge
                                  provenance={lab.provenance_type}
                                  verificationStatus={lab.verification_status}
                                  onClick={() => onInspectProvenance(lab)}
                                />
                              </td>
                              <td className="px-4 py-2.5 text-right">
                                <button
                                  type="button"
                                  onClick={() => onInspectProvenance(lab)}
                                  className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-semibold text-sky-700 bg-sky-50 hover:bg-sky-100 border border-sky-200 rounded-lg shadow-2xs transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-sky-500/30"
                                  title="Trace source document, page location, and verbatim evidence quote"
                                  aria-label={`Trace source evidence for ${lab.test_name}`}
                                >
                                  <FileText className="w-3.5 h-3.5 text-sky-600" />
                                  <span>Trace Source</span>
                                  <span className="text-[10px] font-mono text-sky-600 bg-white px-1 py-0.2 rounded border border-sky-200 ml-0.5">
                                    p. {lab.page_number}
                                  </span>
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
