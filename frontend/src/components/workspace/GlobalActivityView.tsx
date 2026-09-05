import React, { useState, useEffect } from 'react';
import { Patient, AuditLogEntry } from '../../types';
import { auditApi } from '../../services/api';
import {
  Activity,
  CheckCircle2,
  UploadCloud,
  UserPlus,
  Edit2,
  XCircle,
  AlertTriangle,
  Search,
  RefreshCw,
  Clock,
  ChevronDown,
  ChevronRight
} from 'lucide-react';

interface GlobalActivityViewProps {
  patients: Patient[];
  onSelectPatient: (patient: Patient) => void;
}

export const GlobalActivityView: React.FC<GlobalActivityViewProps> = ({
  patients,
  onSelectPatient,
}) => {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const data = await auditApi.getLogs();
      setLogs(data);
    } catch (err) {
      console.error('Failed to load audit logs', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  const patientMap = new Map<string, Patient>();
  patients.forEach((p) => patientMap.set(p.id, p));

  const filteredLogs = logs.filter((log) => {
    const q = searchQuery.toLowerCase();
    return (
      log.action.toLowerCase().includes(q) ||
      (log.patient_name && log.patient_name.toLowerCase().includes(q)) ||
      (log.entity_affected && log.entity_affected.toLowerCase().includes(q)) ||
      (log.user_name && log.user_name.toLowerCase().includes(q))
    );
  });

  const getActionBadge = (action: string) => {
    switch (action) {
      case 'CREATE_PATIENT':
        return {
          icon: <UserPlus className="w-3.5 h-3.5 text-sky-600" />,
          label: 'Patient Registered',
          bg: 'bg-sky-50 text-sky-800 border-sky-200',
        };
      case 'UPLOAD_AND_EXTRACT_REPORT':
        return {
          icon: <UploadCloud className="w-3.5 h-3.5 text-teal-600" />,
          label: 'Document Ingestion',
          bg: 'bg-teal-50 text-teal-800 border-teal-200',
        };
      case 'VERIFY_LAB_RESULT':
        return {
          icon: <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />,
          label: 'Finding Verified',
          bg: 'bg-emerald-50 text-emerald-800 border-emerald-200',
        };
      case 'EDIT_LAB_RESULT':
        return {
          icon: <Edit2 className="w-3.5 h-3.5 text-indigo-600" />,
          label: 'Finding Edited',
          bg: 'bg-indigo-50 text-indigo-800 border-indigo-200',
        };
      case 'REJECT_LAB_RESULT':
        return {
          icon: <XCircle className="w-3.5 h-3.5 text-rose-600" />,
          label: 'Finding Rejected',
          bg: 'bg-rose-50 text-rose-800 border-rose-200',
        };
      case 'ACKNOWLEDGE_CONFLICT':
        return {
          icon: <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />,
          label: 'Conflict Acknowledged',
          bg: 'bg-amber-50 text-amber-800 border-amber-200',
        };
      default:
        return {
          icon: <Activity className="w-3.5 h-3.5 text-slate-600" />,
          label: action.replace(/_/g, ' '),
          bg: 'bg-slate-50 text-slate-800 border-slate-200',
        };
    }
  };

  return (
    <div className="space-y-4 max-w-5xl mx-auto p-4 sm:p-6">
      {/* Header */}
      <div className="bg-white p-5 rounded-xl border border-slate-200/90 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-900">Organization Audit & Activity Log</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Cryptographically sealed and tamper-evident clinical trail of intake, ingestions, and clinician verifications
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search audit trail..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-300 w-52"
            />
          </div>

          <button
            type="button"
            onClick={fetchLogs}
            disabled={loading}
            className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-600 transition-colors cursor-pointer"
            title="Refresh logs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Audit Log Timeline */}
      <div className="bg-white rounded-xl border border-slate-200/90 shadow-2xs overflow-hidden">
        {loading ? (
          <div className="py-12 text-center text-xs text-slate-400">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-slate-400" />
            Loading organization activity trail...
          </div>
        ) : filteredLogs.length === 0 ? (
          <div className="py-12 text-center text-xs text-slate-400">
            No audit records matching criteria.
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {filteredLogs.map((log) => {
              const badge = getActionBadge(log.action);
              const patient = log.patient_id ? patientMap.get(log.patient_id) : null;
              const isExpanded = expandedLogId === log.id;

              return (
                <div
                  key={log.id}
                  className="p-4 hover:bg-slate-50/50 transition-colors text-xs space-y-2"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2.5 flex-wrap">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-semibold border ${badge.bg}`}
                      >
                        {badge.icon}
                        {badge.label}
                      </span>

                      {log.entity_affected && (
                        <span className="font-semibold text-slate-900">
                          {log.entity_affected}
                        </span>
                      )}

                      {patient && (
                        <button
                          type="button"
                          onClick={() => onSelectPatient(patient)}
                          className="text-slate-500 hover:text-slate-900 font-medium cursor-pointer"
                        >
                          for <strong className="text-slate-800 underline">{patient.full_name}</strong>
                          <span className="font-mono text-[10px] text-slate-400 ml-1">({patient.patient_id})</span>
                        </button>
                      )}
                    </div>

                    <div className="flex items-center gap-3 text-[11px] text-slate-400 shrink-0">
                      <span className="text-slate-600 font-medium">{log.user_name || 'Clinician'}</span>
                      <span>•</span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} • {new Date(log.timestamp).toLocaleDateString()}
                      </span>
                      {log.details && Object.keys(log.details).length > 0 && (
                        <button
                          type="button"
                          onClick={() => setExpandedLogId(isExpanded ? null : log.id)}
                          className="text-slate-400 hover:text-slate-600 cursor-pointer"
                        >
                          {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Expanded metadata */}
                  {isExpanded && log.details && (
                    <div className="mt-2 p-3 bg-slate-900 text-slate-200 rounded-lg font-mono text-[11px] overflow-x-auto">
                      <pre>{JSON.stringify(log.details, null, 2)}</pre>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
