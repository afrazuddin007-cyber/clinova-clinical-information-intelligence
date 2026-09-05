import React, { useState, useEffect } from 'react';
import { PatientSummaryResponse } from '../../types';
import { patientApi } from '../../services/api';
import { ProvenanceBadge } from '../common/ProvenanceBadge';
import { Sparkles, RefreshCw, FileText, CheckCircle } from 'lucide-react';

interface PatientSummaryCardProps {
  patientId: string;
}

export const PatientSummaryCard: React.FC<PatientSummaryCardProps> = ({ patientId }) => {
  const [summaryData, setSummaryData] = useState<PatientSummaryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchSummary = async () => {
    setLoading(true);
    try {
      const data = await patientApi.getSummary(patientId);
      setSummaryData(data);
    } catch (err) {
      console.error('Failed to load patient summary', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSummary();
  }, [patientId]);

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-4 sm:p-5">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-md bg-purple-100 text-purple-700 flex items-center justify-center">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-900">Patient-Friendly Longitudinal Summary</h3>
            <p className="text-[11px] text-slate-500">Record-grounded synthesis for clinical review</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <ProvenanceBadge provenance="AI_GENERATED" />
          {summaryData && (
            <span className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
              <CheckCircle className="w-3 h-3 text-emerald-500" />
              {summaryData.grounded_record_count} items referenced
            </span>
          )}
          <button
            type="button"
            onClick={fetchSummary}
            disabled={loading}
            className="p-1 text-slate-400 hover:text-slate-600 rounded transition-colors"
            title="Refresh summary"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {loading ? (
        <div className="py-6 flex flex-col items-center justify-center text-slate-400 gap-2">
          <RefreshCw className="w-5 h-5 animate-spin text-purple-500" />
          <span className="text-xs">Synthesizing records...</span>
        </div>
      ) : summaryData ? (
        <div>
          <p className="text-xs sm:text-sm text-slate-700 leading-relaxed bg-purple-50/30 p-3.5 rounded-lg border border-purple-100/60">
            {summaryData.summary}
          </p>
          <div className="mt-2 text-[10px] text-slate-400 italic">
            {summaryData.disclaimer}
          </div>
        </div>
      ) : (
        <div className="text-xs text-slate-400 py-3">No summary could be generated.</div>
      )}
    </div>
  );
};
