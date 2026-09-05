import React from 'react';
import { Inconsistency } from '../../types';
import { conflictApi } from '../../services/api';
import { AlertTriangle, CheckCircle, ShieldAlert, FileText, User } from 'lucide-react';

interface ConflictsBannerProps {
  conflicts: Inconsistency[];
  onConflictUpdated: () => void;
}

export const ConflictsBanner: React.FC<ConflictsBannerProps> = ({
  conflicts,
  onConflictUpdated,
}) => {
  if (conflicts.length === 0) {
    return (
      <div className="bg-emerald-50/70 border border-emerald-200/80 rounded-xl p-4 flex items-center gap-3 text-xs text-emerald-800">
        <CheckCircle className="w-5 h-5 text-emerald-600 shrink-0" />
        <div>
          <span className="font-bold block">No Record Inconsistencies Detected</span>
          All documented medications, allergies, and demographic parameters align across intake and uploaded reports.
        </div>
      </div>
    );
  }

  const handleAcknowledge = async (id: string) => {
    try {
      await conflictApi.acknowledge(id);
      onConflictUpdated();
    } catch (err) {
      console.error('Failed to acknowledge conflict', err);
    }
  };

  return (
    <div className="space-y-3">
      <div className="bg-amber-500/10 border-l-4 border-amber-500 p-4 rounded-r-xl flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5">
          <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5 shrink-0" />
          <div>
            <h4 className="text-sm font-bold text-amber-900">
              {conflicts.length} Cross-Record Discrepanc{conflicts.length === 1 ? 'y' : 'ies'} Flagged
            </h4>
            <p className="text-xs text-amber-800 mt-0.5">
              Clinova flags contradictory information across intake and diagnostic records for physician reconciliation. The system does not decide medical truth.
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-3">
        {conflicts.map((conflict) => {
          const isAcknowledged = conflict.resolution_status === 'ACKNOWLEDGED';

          return (
            <div
              key={conflict.id}
              className={`p-4 rounded-xl border transition-all ${
                isAcknowledged
                  ? 'bg-slate-50 border-slate-200 opacity-70'
                  : 'bg-white border-amber-200 shadow-xs'
              }`}
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-amber-100 text-amber-900">
                    {conflict.category} Conflict
                  </span>
                  <span className="text-xs font-bold text-slate-900">
                    Target: {conflict.entity_name}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  {isAcknowledged ? (
                    <span className="text-[11px] font-semibold text-slate-500 flex items-center gap-1">
                      <CheckCircle className="w-3.5 h-3.5 text-slate-400" />
                      Reviewed by Physician
                    </span>
                  ) : (
                    <button
                      type="button"
                      onClick={() => handleAcknowledge(conflict.id)}
                      className="px-3 py-1 rounded-lg text-xs font-semibold bg-amber-600 hover:bg-amber-700 text-white transition-colors cursor-pointer shadow-xs"
                    >
                      Acknowledge Review
                    </button>
                  )}
                </div>
              </div>

              {/* Side-by-Side Sources */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                {/* Source A */}
                <div className="p-3 rounded-lg bg-slate-50 border border-slate-200/80">
                  <div className="text-[11px] font-semibold text-slate-500 mb-1 flex items-center gap-1">
                    <User className="w-3 h-3 text-slate-400" />
                    Source A: {conflict.source_a.type}
                  </div>
                  <p className="font-medium text-slate-800">{conflict.source_a.text}</p>
                </div>

                {/* Source B */}
                <div className="p-3 rounded-lg bg-amber-50/50 border border-amber-200/80">
                  <div className="text-[11px] font-semibold text-amber-800 mb-1 flex items-center gap-1">
                    <FileText className="w-3 h-3 text-amber-600" />
                    Source B: {conflict.source_b.type} {conflict.source_b.page ? `(Page ${conflict.source_b.page})` : ''}
                  </div>
                  <p className="font-medium text-amber-900">{conflict.source_b.text}</p>
                </div>
              </div>

              <div className="mt-2.5 text-[11px] text-slate-500">
                {conflict.conflict_description}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
