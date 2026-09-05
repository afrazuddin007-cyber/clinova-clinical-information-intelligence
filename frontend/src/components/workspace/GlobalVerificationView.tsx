import React, { useState, useEffect, useMemo, useRef } from 'react';
import { Patient, ExtractedLabResult } from '../../types';
import { verificationApi } from '../../services/api';
import { RangeStatusBadge } from '../common/RangeStatusBadge';
import {
  CheckSquare,
  CheckCircle2,
  Check,
  Edit2,
  X,
  FileText,
  RefreshCw,
  ArrowRight,
  ShieldCheck
} from 'lucide-react';

interface GlobalVerificationViewProps {
  patients: Patient[];
  onSelectPatient: (patient: Patient, tab?: string) => void;
  onInspectProvenance: (lab: ExtractedLabResult) => void;
  onQueueChanged: () => void;
}

export const GlobalVerificationView: React.FC<GlobalVerificationViewProps> = ({
  patients,
  onSelectPatient,
  onInspectProvenance,
  onQueueChanged,
}) => {
  const [pendingItems, setPendingItems] = useState<ExtractedLabResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const isMountedRef = useRef(true);

  // Edit State
  const [editingItem, setEditingItem] = useState<ExtractedLabResult | null>(null);
  const [newValue, setNewValue] = useState('');
  const [newRange, setNewRange] = useState('');
  const [newUnit, setNewUnit] = useState('');
  const [editReason, setEditReason] = useState('');

  // Reject State
  const [rejectingItem, setRejectingItem] = useState<ExtractedLabResult | null>(null);
  const [rejectReason, setRejectReason] = useState('');

  const fetchPending = async () => {
    setLoading(true);
    try {
      const data = await verificationApi.getPending();
      if (isMountedRef.current) {
        setPendingItems(data);
      }
    } catch (err) {
      console.error('Failed to load pending verifications', err);
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
  };

  useEffect(() => {
    isMountedRef.current = true;
    fetchPending();
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const patientMap = useMemo(() => {
    const map = new Map<string, Patient>();
    patients.forEach((p) => map.set(p.id, p));
    return map;
  }, [patients]);

  const handleVerify = async (labId: string) => {
    setActionLoading(true);
    try {
      await verificationApi.verify(labId);
      await fetchPending();
      onQueueChanged();
    } catch (err) {
      console.error('Failed to verify item', err);
    } finally {
      setActionLoading(false);
    }
  };

  const submitEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingItem || !editReason.trim()) return;

    setActionLoading(true);
    try {
      await verificationApi.edit(editingItem.id, {
        new_value: newValue.trim(),
        new_reference_range: newRange.trim(),
        new_unit: newUnit.trim(),
        edit_reason: editReason.trim(),
      });
      setEditingItem(null);
      await fetchPending();
      onQueueChanged();
    } catch (err) {
      console.error('Failed to edit item', err);
    } finally {
      setActionLoading(false);
    }
  };

  const submitReject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rejectingItem || !rejectReason.trim()) return;

    setActionLoading(true);
    try {
      await verificationApi.reject(rejectingItem.id, rejectReason.trim());
      setRejectingItem(null);
      await fetchPending();
      onQueueChanged();
    } catch (err) {
      console.error('Failed to reject item', err);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-4 max-w-6xl mx-auto p-4 sm:p-6">
      {/* Header */}
      <div className="bg-white p-5 rounded-xl border border-slate-200/90 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-bold text-slate-900">Organization Verification Worklist</h2>
            <span className="px-2 py-0.5 rounded-full text-xs font-bold font-mono bg-amber-100 text-amber-900">
              {pendingItems.length} Pending
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Audit and approve AI-extracted findings across all active patient records prior to permanent persistence
          </p>
        </div>

        <button
          type="button"
          onClick={fetchPending}
          disabled={loading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 rounded-lg shadow-2xs transition-colors cursor-pointer self-start sm:self-center"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Queue items */}
      <div className="bg-white rounded-xl border border-slate-200/90 shadow-2xs overflow-hidden">
        {loading ? (
          <div className="py-12 text-center text-xs text-slate-400">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-slate-400" />
            Loading pending verification findings...
          </div>
        ) : pendingItems.length === 0 ? (
          <div className="py-12 text-center text-xs text-slate-500">
            <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto mb-2" />
            <h4 className="text-sm font-bold text-slate-800">Verification Queue Clear</h4>
            <p className="text-xs text-slate-400 mt-1">
              All extracted clinical parameters across all organization patients are verified.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {pendingItems.map((lab) => {
              const patient = patientMap.get(lab.patient_id);
              return (
                <div
                  key={lab.id}
                  className="p-4 hover:bg-slate-50/50 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-4"
                >
                  <div className="space-y-1">
                    {/* Patient & Test Tag */}
                    <div className="flex items-center gap-2 flex-wrap">
                      {patient ? (
                        <button
                          type="button"
                          onClick={() => onSelectPatient(patient, 'VERIFY')}
                          className="font-semibold text-xs text-slate-800 hover:text-slate-900 hover:underline cursor-pointer flex items-center gap-1"
                        >
                          <span>{patient.full_name}</span>
                          <span className="font-mono text-[10px] text-slate-400">({patient.patient_id})</span>
                        </button>
                      ) : (
                        <span className="text-xs text-slate-400">Patient ID: {lab.patient_id}</span>
                      )}

                      <span>•</span>
                      <span className="text-xs font-bold text-slate-900">{lab.test_name}</span>
                      <RangeStatusBadge status={lab.range_status} />
                    </div>

                    {/* Values & Range */}
                    <div className="text-xs text-slate-600 flex items-center gap-3 flex-wrap">
                      <span>
                        Measured: <strong className="text-slate-900 font-mono">{lab.raw_value} {lab.unit || ''}</strong>
                      </span>
                      <span>•</span>
                      <span>
                        Source Range: <span className="font-mono text-slate-700">{lab.raw_reference_range || 'None provided'}</span>
                      </span>
                      <span>•</span>
                      <button
                        type="button"
                        onClick={() => onInspectProvenance(lab)}
                        className="text-sky-600 hover:text-sky-800 underline flex items-center gap-1 cursor-pointer font-medium text-[11px]"
                      >
                        <FileText className="w-3 h-3" />
                        Provenance Snippet
                      </button>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 self-end md:self-center">
                    <button
                      type="button"
                      disabled={actionLoading}
                      onClick={() => handleVerify(lab.id)}
                      className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-2xs transition-colors cursor-pointer"
                    >
                      <Check className="w-3.5 h-3.5" />
                      Approve
                    </button>

                    <button
                      type="button"
                      disabled={actionLoading}
                      onClick={() => {
                        setEditingItem(lab);
                        setNewValue(lab.raw_value);
                        setNewRange(lab.raw_reference_range || '');
                        setNewUnit(lab.unit || '');
                        setEditReason('');
                      }}
                      className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-100 text-slate-700 text-xs font-semibold transition-colors cursor-pointer shadow-2xs"
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                      Edit
                    </button>

                    <button
                      type="button"
                      disabled={actionLoading}
                      onClick={() => {
                        setRejectingItem(lab);
                        setRejectReason('');
                      }}
                      className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-rose-200 hover:bg-rose-50 text-rose-700 text-xs font-semibold transition-colors cursor-pointer shadow-2xs"
                    >
                      <X className="w-3.5 h-3.5" />
                      Reject
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Edit Modal */}
      {editingItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white rounded-xl border border-slate-200 shadow-2xl max-w-md w-full p-5">
            <h4 className="text-sm font-bold text-slate-900 mb-1">
              Edit Finding: {editingItem.test_name}
            </h4>
            <p className="text-xs text-slate-500 mb-4">
              Original AI Value: <span className="font-mono font-bold text-slate-800">{editingItem.raw_value}</span> (preserved in audit log).
            </p>

            <form onSubmit={submitEdit} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Corrected Value</label>
                <input
                  type="text"
                  required
                  value={newValue}
                  onChange={(e) => setNewValue(e.target.value)}
                  className="w-full px-3 py-1.5 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-400"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Units</label>
                  <input
                    type="text"
                    value={newUnit}
                    onChange={(e) => setNewUnit(e.target.value)}
                    className="w-full px-3 py-1.5 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-400"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Reference Range</label>
                  <input
                    type="text"
                    value={newRange}
                    onChange={(e) => setNewRange(e.target.value)}
                    className="w-full px-3 py-1.5 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-400"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Clinical Audit Reason <span className="text-rose-500">*</span>
                </label>
                <textarea
                  required
                  rows={2}
                  value={editReason}
                  onChange={(e) => setEditReason(e.target.value)}
                  placeholder="Document why this value was updated..."
                  className="w-full px-3 py-1.5 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-400"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setEditingItem(null)}
                  className="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-1.5 text-xs font-semibold bg-slate-900 hover:bg-slate-800 text-white rounded-lg cursor-pointer"
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
          <div className="bg-white rounded-xl border border-slate-200 shadow-2xl max-w-md w-full p-5">
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
                  className="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-1.5 text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white rounded-lg cursor-pointer"
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
