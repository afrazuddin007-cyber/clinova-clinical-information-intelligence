import React, { useState, useEffect, useMemo, useRef } from 'react';
import { Patient, MedicalReport } from '../../types';
import { reportApi } from '../../services/api';
import {
  FileText,
  Search,
  ExternalLink,
  Calendar,
  Building2,
  ArrowRight,
  RefreshCw,
  Clock
} from 'lucide-react';

interface GlobalReportsViewProps {
  patients: Patient[];
  onSelectPatient: (patient: Patient, tab?: string) => void;
}

export const GlobalReportsView: React.FC<GlobalReportsViewProps> = ({
  patients,
  onSelectPatient,
}) => {
  const [reports, setReports] = useState<MedicalReport[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const isMountedRef = useRef(true);

  const fetchReports = async () => {
    setLoading(true);
    try {
      const data = await reportApi.listAll();
      if (isMountedRef.current) {
        setReports(data);
      }
    } catch (err) {
      console.error('Failed to load organization reports', err);
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
  };

  useEffect(() => {
    isMountedRef.current = true;
    fetchReports();
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const patientMap = useMemo(() => {
    const map = new Map<string, Patient>();
    patients.forEach((p) => map.set(p.id, p));
    return map;
  }, [patients]);

  const filteredReports = useMemo(() => {
    const q = searchQuery.toLowerCase();
    return reports.filter((r) => {
      const patient = patientMap.get(r.patient_id);
      return (
        r.original_file_name.toLowerCase().includes(q) ||
        (r.report_title && r.report_title.toLowerCase().includes(q)) ||
        (r.facility_name && r.facility_name.toLowerCase().includes(q)) ||
        (patient && (patient.full_name.toLowerCase().includes(q) || patient.patient_id.toLowerCase().includes(q)))
      );
    });
  }, [reports, searchQuery, patientMap]);

  return (
    <div className="space-y-4 max-w-6xl mx-auto p-4 sm:p-6">
      {/* Header bar */}
      <div className="bg-white p-5 rounded-xl border border-slate-200/90 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-900">Organization Medical Records</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Preserved source clinical documents across all patients in your workspace ({reports.length} total)
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by file or patient..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-300 w-56"
            />
          </div>

          <button
            type="button"
            onClick={fetchReports}
            disabled={loading}
            className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-600 transition-colors cursor-pointer"
            title="Refresh repository"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Repository Table */}
      <div className="bg-white rounded-xl border border-slate-200/90 shadow-2xs overflow-hidden">
        {loading ? (
          <div className="py-12 text-center text-xs text-slate-400">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-slate-400" />
            Loading organization medical records...
          </div>
        ) : filteredReports.length === 0 ? (
          <div className="py-12 text-center text-xs text-slate-400">
            No medical records match the query.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50/80 border-b border-slate-200/80 text-[11px] text-slate-500 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3">Document Title / File</th>
                  <th className="px-4 py-3">Patient</th>
                  <th className="px-4 py-3">Report Date</th>
                  <th className="px-4 py-3">Facility</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Findings</th>
                  <th className="px-4 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-normal">
                {filteredReports.map((report) => {
                  const patient = patientMap.get(report.patient_id);
                  return (
                    <tr key={report.id} className="hover:bg-slate-50/60 transition-colors">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2.5">
                          <div className="w-7 h-7 rounded-lg bg-slate-100 text-slate-700 flex items-center justify-center shrink-0">
                            <FileText className="w-3.5 h-3.5" />
                          </div>
                          <div className="overflow-hidden">
                            <div className="font-semibold text-slate-900 truncate">
                              {report.report_title || report.original_file_name}
                            </div>
                            <div className="text-[11px] text-slate-400 font-mono truncate">
                              {report.original_file_name}
                            </div>
                          </div>
                        </div>
                      </td>

                      <td className="px-4 py-3">
                        {patient ? (
                          <button
                            type="button"
                            onClick={() => onSelectPatient(patient, 'RECORDS')}
                            className="text-left group cursor-pointer"
                          >
                            <div className="font-semibold text-slate-800 group-hover:text-slate-900 group-hover:underline">
                              {patient.full_name}
                            </div>
                            <span className="font-mono text-[10px] text-slate-400">
                              {patient.patient_id}
                            </span>
                          </button>
                        ) : (
                          <span className="text-slate-400">Unknown Patient</span>
                        )}
                      </td>

                      <td className="px-4 py-3 text-slate-600">
                        {report.report_date
                          ? new Date(report.report_date).toLocaleDateString()
                          : new Date(report.uploaded_at).toLocaleDateString()}
                      </td>

                      <td className="px-4 py-3 text-slate-600">
                        {report.facility_name || '—'}
                      </td>

                      <td className="px-4 py-3">
                        <span
                          className={`text-[10px] font-semibold px-2 py-0.5 rounded ${
                            report.processing_status === 'EXTRACTED'
                              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                              : 'bg-sky-50 text-sky-700 border border-sky-200'
                          }`}
                        >
                          {report.processing_status}
                        </span>
                      </td>

                      <td className="px-4 py-3 font-semibold text-slate-700">
                        {report.lab_count} test{report.lab_count !== 1 ? 's' : ''}
                      </td>

                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <a
                            href={reportApi.getFileUrl(report.id)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 rounded-md transition-colors shadow-2xs"
                          >
                            <ExternalLink className="w-3 h-3 text-slate-400" />
                            File
                          </a>

                          {patient && (
                            <button
                              type="button"
                              onClick={() => onSelectPatient(patient, 'RECORDS')}
                              className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-md transition-colors shadow-2xs cursor-pointer"
                            >
                              Profile
                              <ArrowRight className="w-3 h-3" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
