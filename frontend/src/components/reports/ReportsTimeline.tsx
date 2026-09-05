import React from 'react';
import { MedicalReport } from '../../types';
import { FileText, Calendar, Layers, Eye, CheckCircle2, AlertTriangle, UploadCloud } from 'lucide-react';

interface ReportsTimelineProps {
  reports: MedicalReport[];
  onUploadClick: () => void;
  onViewReport: (report: MedicalReport) => void;
  onCompareSelect?: (reportAId: string, reportBId: string) => void;
}

export const ReportsTimeline: React.FC<ReportsTimelineProps> = ({
  reports,
  onUploadClick,
  onViewReport,
  onCompareSelect,
}) => {
  return (
    <div className="bg-white rounded-xl border border-slate-200/90 shadow-xs p-4 sm:p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <FileText className="w-4 h-4 text-sky-600" />
            Preserved Medical Reports ({reports.length})
          </h3>
          <p className="text-[11px] text-slate-500">Chronological repository of all uploaded source documents</p>
        </div>
        <button
          type="button"
          onClick={onUploadClick}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-sky-50 text-sky-700 hover:bg-sky-100 border border-sky-200 text-xs font-semibold transition-colors cursor-pointer"
        >
          <UploadCloud className="w-3.5 h-3.5" />
          Upload Report
        </button>
      </div>

      {reports.length === 0 ? (
        <div className="py-8 text-center border-2 border-dashed border-slate-200 rounded-xl bg-slate-50/50">
          <FileText className="w-8 h-8 text-slate-300 mx-auto mb-2" />
          <div className="text-xs font-semibold text-slate-600">No medical reports uploaded yet</div>
          <p className="text-[11px] text-slate-400 max-w-xs mx-auto mt-1 mb-3">
            Upload diagnostic lab panels or clinical summaries to extract structured results.
          </p>
          <button
            type="button"
            onClick={onUploadClick}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold text-white bg-sky-600 hover:bg-sky-700 rounded-lg shadow-xs"
          >
            <UploadCloud className="w-3.5 h-3.5" />
            Upload First Report
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {reports.map((report, idx) => {
            const isLatest = idx === 0;
            const dateDisplay = report.report_date
              ? new Date(report.report_date).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
              : new Date(report.uploaded_at).toLocaleDateString();

            return (
              <div
                key={report.id}
                className="group p-3.5 rounded-xl border border-slate-200 bg-white hover:border-sky-300 hover:shadow-xs transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3"
              >
                <div className="flex items-start gap-3">
                  <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${isLatest ? 'bg-sky-100 text-sky-700' : 'bg-slate-100 text-slate-600'}`}>
                    <FileText className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-slate-900 group-hover:text-sky-600 transition-colors">
                        {report.original_file_name}
                      </span>
                      {isLatest && (
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-100 text-emerald-800">
                          Latest
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 text-[11px] text-slate-500 mt-1">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3 text-slate-400" />
                        {dateDisplay}
                      </span>
                      <span>•</span>
                      <span className="flex items-center gap-1">
                        <Layers className="w-3 h-3 text-slate-400" />
                        {report.lab_count} Lab Tests
                      </span>
                      <span>•</span>
                      <span>{(report.file_size_bytes / 1024).toFixed(0)} KB</span>
                    </div>
                  </div>
                </div>

                {/* Report Actions */}
                <div className="flex items-center gap-2 self-end sm:self-center">
                  <button
                    type="button"
                    onClick={() => onViewReport(report)}
                    className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-xs font-medium text-slate-700 transition-colors cursor-pointer"
                    title="Inspect original document"
                  >
                    <Eye className="w-3.5 h-3.5 text-slate-500" />
                    View Original
                  </button>

                  {reports.length >= 2 && idx === 0 && onCompareSelect && (
                    <button
                      type="button"
                      onClick={() => onCompareSelect(reports[1].id, reports[0].id)}
                      className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-teal-50 border border-teal-200 hover:bg-teal-100 text-teal-800 text-xs font-semibold transition-colors cursor-pointer"
                      title="Compare against previous report"
                    >
                      Compare with Previous
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
