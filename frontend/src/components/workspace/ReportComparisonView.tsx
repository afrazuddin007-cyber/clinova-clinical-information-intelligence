import React, { useState, useEffect } from 'react';
import { MedicalReport, ReportComparisonResponse } from '../../types';
import { comparisonApi } from '../../services/api';
import { RangeStatusBadge } from '../common/RangeStatusBadge';
import { ArrowRight, GitCompare, RefreshCw, AlertCircle, PlusCircle, CheckCircle2, HelpCircle } from 'lucide-react';

interface ReportComparisonViewProps {
  patientId: string;
  reports: MedicalReport[];
  initialReportAId?: string;
  initialReportBId?: string;
}

export const ReportComparisonView: React.FC<ReportComparisonViewProps> = ({
  patientId,
  reports,
  initialReportAId,
  initialReportBId,
}) => {
  const [reportAId, setReportAId] = useState<string>(
    initialReportAId || (reports.length >= 2 ? reports[1].id : reports[0]?.id || '')
  );
  const [reportBId, setReportBId] = useState<string>(
    initialReportBId || (reports.length >= 1 ? reports[0]?.id || '' : '')
  );

  const [comparisonData, setComparisonData] = useState<ReportComparisonResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fetchComparison = async () => {
    if (!reportAId || !reportBId || reportAId === reportBId) {
      setComparisonData(null);
      return;
    }

    setLoading(true);
    setErrorMessage(null);
    try {
      const data = await comparisonApi.compare(patientId, reportAId, reportBId);
      setComparisonData(data);
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Failed to compare reports.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (reports.length >= 2 && (!reportAId || !reportBId || reportAId === reportBId)) {
      setReportAId(reports[1].id);
      setReportBId(reports[0].id);
    }
  }, [reports]);

  useEffect(() => {
    if (reportAId && reportBId && reportAId !== reportBId) {
      fetchComparison();
    }
  }, [reportAId, reportBId]);

  if (reports.length < 2) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-8 text-center">
        <GitCompare className="w-10 h-10 text-slate-300 mx-auto mb-3" />
        <h3 className="text-sm font-bold text-slate-800">At least 2 reports required for comparison</h3>
        <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1">
          Upload a baseline and follow-up medical report to inspect changes, new additions, and quantitative lab deltas.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Comparison Selector Bar */}
      <div className="bg-white rounded-xl border border-slate-200/90 shadow-xs p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-teal-100 text-teal-700 flex items-center justify-center">
            <GitCompare className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900">Longitudinal Report Comparison</h3>
            <p className="text-[11px] text-slate-500">Deterministic delta calculation between any two historical records</p>
          </div>
        </div>

        {/* Dropdowns */}
        <div className="flex items-center gap-2 text-xs">
          <div className="flex items-center gap-1.5">
            <span className="font-semibold text-slate-500">Baseline (Older):</span>
            <select
              value={reportAId}
              onChange={(e) => setReportAId(e.target.value)}
              className="px-2.5 py-1.5 border border-slate-200 rounded-lg bg-slate-50 font-medium text-slate-800"
            >
              {reports.map((r) => (
                <option key={`a-${r.id}`} value={r.id}>
                  {r.original_file_name} ({new Date(r.report_date || r.uploaded_at).toLocaleDateString()})
                </option>
              ))}
            </select>
          </div>

          <ArrowRight className="w-4 h-4 text-slate-400 shrink-0" />

          <div className="flex items-center gap-1.5">
            <span className="font-semibold text-slate-500">Target (Newer):</span>
            <select
              value={reportBId}
              onChange={(e) => setReportBId(e.target.value)}
              className="px-2.5 py-1.5 border border-slate-200 rounded-lg bg-slate-50 font-medium text-slate-800"
            >
              {reports.map((r) => (
                <option key={`b-${r.id}`} value={r.id}>
                  {r.original_file_name} ({new Date(r.report_date || r.uploaded_at).toLocaleDateString()})
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Summary Delta Metric Badges */}
      {comparisonData && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="p-3 bg-white rounded-xl border border-slate-200 shadow-xs flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-sky-100 text-sky-700 flex items-center justify-center">
              <PlusCircle className="w-4 h-4" />
            </div>
            <div>
              <div className="text-lg font-bold text-slate-900">{comparisonData.new_count}</div>
              <div className="text-[11px] font-medium text-slate-500">Newly Added Tests</div>
            </div>
          </div>

          <div className="p-3 bg-white rounded-xl border border-slate-200 shadow-xs flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center">
              <RefreshCw className="w-4 h-4" />
            </div>
            <div>
              <div className="text-lg font-bold text-slate-900">{comparisonData.changed_count}</div>
              <div className="text-[11px] font-medium text-slate-500">Changed Values</div>
            </div>
          </div>

          <div className="p-3 bg-white rounded-xl border border-slate-200 shadow-xs flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center">
              <CheckCircle2 className="w-4 h-4" />
            </div>
            <div>
              <div className="text-lg font-bold text-slate-900">{comparisonData.unchanged_count}</div>
              <div className="text-[11px] font-medium text-slate-500">Identical Values</div>
            </div>
          </div>

          <div className="p-3 bg-white rounded-xl border border-slate-200 shadow-xs flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-slate-100 text-slate-700 flex items-center justify-center">
              <HelpCircle className="w-4 h-4" />
            </div>
            <div>
              <div className="text-lg font-bold text-slate-900">{comparisonData.incomparable_count}</div>
              <div className="text-[11px] font-medium text-slate-500">Incomparable / Omitted</div>
            </div>
          </div>
        </div>
      )}

      {/* Comparison Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        {loading ? (
          <div className="py-12 text-center text-slate-400 text-xs flex flex-col items-center justify-center gap-2">
            <RefreshCw className="w-5 h-5 animate-spin text-teal-600" />
            <span>Computing longitudinal differences...</span>
          </div>
        ) : comparisonData ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                  <th className="py-3 px-4">Test Name</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Baseline Result ({comparisonData.report_a_name.slice(0, 16)}...)</th>
                  <th className="py-3 px-4">Target Result ({comparisonData.report_b_name.slice(0, 16)}...)</th>
                  <th className="py-3 px-4">Delta (Difference)</th>
                  <th className="py-3 px-4">Notes & Observations</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {comparisonData.items.map((item, idx) => {
                  const isChanged = item.status_tag === 'CHANGED';
                  const isNew = item.status_tag === 'NEW';
                  const isUnchanged = item.status_tag === 'UNCHANGED';

                  return (
                    <tr key={idx} className="hover:bg-slate-50/60 transition-colors">
                      <td className="py-3 px-4 font-semibold text-slate-800">
                        {item.test_name}
                      </td>

                      <td className="py-3 px-4">
                        {isNew && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-sky-100 text-sky-800">
                            NEW
                          </span>
                        )}
                        {isChanged && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800">
                            CHANGED
                          </span>
                        )}
                        {isUnchanged && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                            UNCHANGED
                          </span>
                        )}
                        {item.status_tag === 'INCOMPARABLE' && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-600">
                            INCOMPARABLE
                          </span>
                        )}
                      </td>

                      {/* Baseline */}
                      <td className="py-3 px-4 font-mono">
                        {item.report_a_value ? (
                          <div className="flex items-center gap-1.5">
                            <span className="font-bold text-slate-700">{item.report_a_value}</span>
                            {item.unit && <span className="text-slate-400 text-[11px]">{item.unit}</span>}
                            {item.report_a_status && <RangeStatusBadge status={item.report_a_status} className="scale-90" />}
                          </div>
                        ) : (
                          <span className="text-slate-300 italic">Not tested</span>
                        )}
                      </td>

                      {/* Target */}
                      <td className="py-3 px-4 font-mono">
                        {item.report_b_value ? (
                          <div className="flex items-center gap-1.5">
                            <span className="font-bold text-slate-900">{item.report_b_value}</span>
                            {item.unit && <span className="text-slate-400 text-[11px]">{item.unit}</span>}
                            {item.report_b_status && <RangeStatusBadge status={item.report_b_status} className="scale-90" />}
                          </div>
                        ) : (
                          <span className="text-slate-300 italic">Omitted</span>
                        )}
                      </td>

                      {/* Delta */}
                      <td className="py-3 px-4 font-mono font-semibold">
                        {item.delta_display ? (
                          <span
                            className={
                              item.numeric_delta && item.numeric_delta > 0
                                ? 'text-amber-700'
                                : item.numeric_delta && item.numeric_delta < 0
                                ? 'text-sky-700'
                                : 'text-slate-500'
                            }
                          >
                            {item.delta_display}
                          </span>
                        ) : (
                          <span className="text-slate-400 font-normal">—</span>
                        )}
                      </td>

                      {/* Notes */}
                      <td className="py-3 px-4 text-slate-500 text-[11px]">
                        {item.notes || '—'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-12 text-center text-slate-400 text-xs">
            Select two different reports above to execute comparison.
          </div>
        )}
      </div>
    </div>
  );
};
