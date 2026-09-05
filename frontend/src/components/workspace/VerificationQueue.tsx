import React, { useState } from 'react';
import { ExtractedLabResult } from '../../types';
import { verificationApi } from '../../services/api';
import { RangeStatusBadge } from '../common/RangeStatusBadge';
import { Check, Edit2, X, AlertCircle, FileText, CheckCircle2, ArrowRight } from 'lucide-react';

interface VerificationQueueProps {
  labs: ExtractedLabResult[];
  onItemUpdated: () => void;
  onInspectProvenance: (lab: ExtractedLabResult) => void;
}

export const VerificationQueue: React.FC<VerificationQueueProps> = ({
  labs,
  onItemUpdated,
  onInspectProvenance,
}) => {
  const pendingLabs = labs.filter((l) => l.verification_status === 'PENDING_VERIFICATION');

  // Edit State
  const [editingItem, setEditingItem] = useState<ExtractedLabResult | null>(null);
  const [newValue, setNewValue] = useState('');
  const [newRange, setNewRange] = useState('');
  const [newUnit, setNewUnit] = useState('');
  const [editReason, setEditReason] = useState('');

  // Reject State
  const [rejectingItem, setRejectingItem] = useState<ExtractedLabResult | null>(null);
  const [rejectReason, setRejectReason] = useState('');

  const [loading, setLoading] = useState(false);

  const handleVerify = async (labId: string) => {
    setLoading(true);
    try {
      await verificationApi.verify(labId);
      onItemUpdated();
    } catch (err) {
      console.error('Failed to verify lab result', err);
    } finally {
      setLoading(false);
    }
  };

  const startEdit = (lab: ExtractedLabResult) => {
    setEditingItem(lab);
    setNewValue(lab.raw_value);
    setNewRange(lab.raw_reference_range || '');
    setNewUnit(lab.unit || '');
    setEditReason('');
  };

  const submitEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingItem || !editReason.trim()) return;

    setLoading(true);
    try {
      await verificationApi.edit(editingItem.id, {
        new_value: newValue.trim(),
        new_reference_range: newRange.trim(),
        new_unit: newUnit.trim(),
        edit_reason: editReason.trim(),
      });
      setEditingItem(null);
      onItemUpdated();
    } catch (err) {
      console.error('Failed to edit lab result', err);
    } finally {
      setLoading(false);
    }
  };

  const submitReject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rejectingItem || !rejectReason.trim()) return;

    setLoading(true);
    try {
      await verificationApi.reject(rejectingItem.id, rejectReason.trim());
      setRejectingItem(null);
      onItemUpdated();
    } catch (err) {
      console.error('Failed to reject lab result', err);
    } finally {
      setLoading(false);
    }
  };

  if (pendingLabs.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-8 text-center">
        <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto mb-2" />
        <h4 className="text-sm font-bold text-slate-800">Verification Queue Clear</h4>
        <p className="text-xs text-slate-500 mt-1">
          All extracted clinical laboratory values have been reviewed and verified by a licensed clinician.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Visual Lifecycle Progression Banner */}
      <div className="bg-white p-3.5 sm:p-4 rounded-2xl border border-slate-200 shadow-2xs flex items-center justify-between gap-2 overflow-x-auto text-xs font-medium text-slate-600">
        <div className="flex items-center gap-2 shrink-0">
          <span className="w-5 h-5 rounded-full bg-sky-100 text-sky-700 font-bold flex items-center justify-center text-[10px]">1</span>
          <span className="font-semibold text-slate-800">Extracted (AI)</span>
        </div>
        <ArrowRight className="w-3.5 h-3.5 text-slate-400 shrink-0" />
        <div className="flex items-center gap-2 shrink-0">
          <span className="w-5 h-5 rounded-full bg-amber-100 text-amber-700 font-bold flex items-center justify-center text-[10px]">2</span>
          <span className="font-semibold text-amber-900 bg-amber-50 px-2 py-0.5 rounded-md border border-amber-200">Pending Review</span>
        </div>
        <ArrowRight className="w-3.5 h-3.5 text-slate-400 shrink-0" />
        <div className="flex items-center gap-2 shrink-0">
          <span className="w-5 h-5 rounded-full bg-slate-100 text-slate-700 font-bold flex items-center justify-center text-[10px]">3</span>
          <span className="font-semibold text-slate-800">Human Verification</span>
        </div>
        <ArrowRight className="w-3.5 h-3.5 text-slate-400 shrink-0" />
        <div className="flex items-center gap-2 shrink-0">
          <span className="w-5 h-5 rounded-full bg-emerald-100 text-emerald-700 font-bold flex items-center justify-center text-[10px]">4</span>
          <span className="font-semibold text-emerald-800">Verified Record</span>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-200 bg-slate-50/70 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              Clinician Verification Queue ({pendingLabs.length})
            </h3>
            <p className="text-[11px] text-slate-500">
              Audit and approve AI-extracted findings before finalizing into persistent patient records
            </p>
          </div>
        </div>

        <div className="divide-y divide-slate-100">
          {pendingLabs.map((lab) => (
            <div
              key={lab.id}
              className="p-4 hover:bg-slate-50/50 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-4"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-slate-800">{lab.test_name}</span>
                  <RangeStatusBadge status={lab.range_status} />
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-amber-50 text-amber-800 border border-amber-200">
                    Pending Review
                  </span>
                </div>

                <div className="text-xs text-slate-600 flex items-center gap-3">
                  <span>
                    Extracted Value: <strong className="text-slate-900 font-mono">{lab.raw_value} {lab.unit || ''}</strong>
                  </span>
                  <span>•</span>
                  <span>
                    Report Range: <span className="font-mono text-slate-700">{lab.raw_reference_range || 'None provided'}</span>
                  </span>
                  <span>•</span>
                  <button
                    type="button"
                    onClick={() => onInspectProvenance(lab)}
                    className="text-sky-600 hover:text-sky-800 underline flex items-center gap-1 cursor-pointer font-medium"
                  >
                    <FileText className="w-3 h-3" />
                    Snippet: "{lab.source_snippet?.slice(0, 30)}..."
                  </button>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2 self-end md:self-center">
                <button
                  type="button"
                  disabled={loading}
                  onClick={() => handleVerify(lab.id)}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-xs transition-colors cursor-pointer"
                  title="Approve extraction without modification"
                >
                  <Check className="w-3.5 h-3.5" />
                  Verify
                </button>

                <button
                  type="button"
                  disabled={loading}
                  onClick={() => startEdit(lab)}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-100 text-slate-700 text-xs font-semibold transition-colors cursor-pointer"
                  title="Correct value or range with clinical audit rationale"
                >
                  <Edit2 className="w-3.5 h-3.5" />
                  Edit
                </button>

                <button
                  type="button"
                  disabled={loading}
                  onClick={() => {
                    setRejectingItem(lab);
                    setRejectReason('');
                  }}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-rose-200 hover:bg-rose-50 text-rose-700 text-xs font-semibold transition-colors cursor-pointer"
                  title="Reject extraction"
                >
                  <X className="w-3.5 h-3.5" />
                  Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Edit Modal */}
      {editingItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white rounded-xl border border-slate-200 shadow-2xl max-w-md w-full p-5 animate-in fade-in zoom-in-95">
            <h4 className="text-sm font-bold text-slate-900 mb-1">
              Edit Extracted Finding: {editingItem.test_name}
            </h4>
            <p className="text-xs text-slate-500 mb-4">
              Original AI Value: <span className="font-mono font-bold text-slate-800">{editingItem.raw_value}</span> (will be preserved in audit history).
            </p>

            <form onSubmit={submitEdit} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Corrected Value</label>
                <input
                  type="text"
                  required
                  value={newValue}
                  onChange={(e) => setNewValue(e.target.value)}
                  className="w-full px-3 py-1.5 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500/20"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Units</label>
                  <input
                    type="text"
                    value={newUnit}
                    onChange={(e) => setNewUnit(e.target.value)}
                    className="w-full px-3 py-1.5 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500/20"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Reference Range</label>
                  <input
                    type="text"
                    value={newRange}
                    onChange={(e) => setNewRange(e.target.value)}
                    className="w-full px-3 py-1.5 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500/20"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Clinical Reason for Override <span className="text-rose-500">*</span>
                </label>
                <textarea
                  required
                  rows={2}
                  value={editReason}
                  onChange={(e) => setEditReason(e.target.value)}
                  placeholder="e.g. Corrected OCR artifact on lab sheet"
                  className="w-full px-3 py-1.5 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500/20"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setEditingItem(null)}
                  className="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-4 py-1.5 text-xs font-semibold bg-sky-600 hover:bg-sky-700 text-white rounded-lg"
                >
                  Save & Verify
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Reject Modal */}
      {rejectingItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white rounded-xl border border-slate-200 shadow-2xl max-w-md w-full p-5 animate-in fade-in zoom-in-95">
            <h4 className="text-sm font-bold text-rose-900 mb-1">
              Reject Finding: {rejectingItem.test_name}
            </h4>
            <p className="text-xs text-slate-500 mb-4">
              Item will be removed from active longitudinal views with a documented audit record.
            </p>

            <form onSubmit={submitReject} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Rejection Reason <span className="text-rose-500">*</span>
                </label>
                <textarea
                  required
                  rows={2}
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="e.g. Test belongs to external control sample, not patient."
                  className="w-full px-3 py-1.5 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-rose-500/20"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setRejectingItem(null)}
                  className="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-4 py-1.5 text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white rounded-lg"
                >
                  Confirm Rejection
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
