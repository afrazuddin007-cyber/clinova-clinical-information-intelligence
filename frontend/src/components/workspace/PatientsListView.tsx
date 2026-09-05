import React, { useState } from 'react';
import { Patient } from '../../types';
import { Search, Plus, User, FileText, AlertTriangle, ArrowRight, CheckCircle2 } from 'lucide-react';

interface PatientsListViewProps {
  patients: Patient[];
  onSelectPatient: (patient: Patient) => void;
  onNewPatientClick: () => void;
  onLoadDemo: () => void;
  isSeedingDemo: boolean;
}

export const PatientsListView: React.FC<PatientsListViewProps> = ({
  patients,
  onSelectPatient,
  onNewPatientClick,
  onLoadDemo,
  isSeedingDemo,
}) => {
  const [searchQuery, setSearchQuery] = useState('');

  const filteredPatients = patients.filter((p) => {
    const q = searchQuery.toLowerCase().trim();
    if (!q) return true;
    return (
      p.full_name.toLowerCase().includes(q) ||
      p.patient_id.toLowerCase().includes(q) ||
      (p.existing_conditions || '').toLowerCase().includes(q) ||
      (p.allergies || '').toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Top Header & Search Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Patients</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Manage persistent patient records and medical histories across your organization.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          {/* Search Box */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by name or ID (e.g. CL-8F29K4)..."
              className="pl-8.5 pr-3 py-1.5 text-xs border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-slate-900/10 focus:border-slate-400 w-64 shadow-2xs"
            />
          </div>

          {/* New Patient Button */}
          <button
            type="button"
            onClick={onNewPatientClick}
            className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg transition-colors shadow-xs cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            New Patient
          </button>
        </div>
      </div>

      {/* Patients Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
        {patients.length === 0 ? (
          /* Empty Patients State */
          <div className="py-16 text-center px-4">
            <div className="w-10 h-10 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto mb-3">
              <User className="w-5 h-5" />
            </div>
            <h3 className="text-sm font-bold text-slate-800">No Patient Records Yet</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 mb-5">
              Create your organization's first patient profile to begin structured document ingestion.
            </p>
            <div className="flex items-center justify-center gap-3">
              <button
                type="button"
                onClick={onNewPatientClick}
                className="px-4 py-2 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg shadow-xs cursor-pointer"
              >
                Create First Patient
              </button>
              <button
                type="button"
                onClick={onLoadDemo}
                disabled={isSeedingDemo}
                className="px-4 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200/80 rounded-lg transition-colors cursor-pointer"
              >
                {isSeedingDemo ? 'Loading...' : 'Load Demo Patient'}
              </button>
            </div>
          </div>
        ) : filteredPatients.length === 0 ? (
          <div className="py-12 text-center text-slate-400 text-xs">
            No patients match "<span className="font-semibold text-slate-600">{searchQuery}</span>".
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/70 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                  <th className="py-3 px-4">Patient ID</th>
                  <th className="py-3 px-4">Name</th>
                  <th className="py-3 px-4">Age / Sex</th>
                  <th className="py-3 px-4">Documented Conditions</th>
                  <th className="py-3 px-4">Reports</th>
                  <th className="py-3 px-4">Status & Review</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredPatients.map((p) => {
                  const hasPending = p.pending_verifications_count > 0;
                  const hasConflicts = p.conflict_count > 0;

                  return (
                    <tr
                      key={p.id}
                      onClick={() => onSelectPatient(p)}
                      className="hover:bg-slate-50/70 transition-colors cursor-pointer group"
                    >
                      {/* Patient ID */}
                      <td className="py-3.5 px-4 font-mono font-semibold text-slate-700">
                        <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-800 border border-slate-200/80">
                          {p.patient_id}
                        </span>
                      </td>

                      {/* Name */}
                      <td className="py-3.5 px-4 font-semibold text-slate-900 group-hover:text-sky-600 transition-colors">
                        {p.full_name}
                      </td>

                      {/* Age & Sex */}
                      <td className="py-3.5 px-4 text-slate-600 capitalize">
                        {p.age}y • {p.sex}
                      </td>

                      {/* Conditions */}
                      <td className="py-3.5 px-4 text-slate-600 max-w-xs truncate">
                        {p.existing_conditions || 'None documented'}
                      </td>

                      {/* Reports Count */}
                      <td className="py-3.5 px-4">
                        <span className="inline-flex items-center gap-1 font-medium text-slate-700">
                          <FileText className="w-3.5 h-3.5 text-slate-400" />
                          {p.report_count}
                        </span>
                      </td>

                      {/* Status / Reviews */}
                      <td className="py-3.5 px-4">
                        {hasConflicts ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-50 text-amber-800 border border-amber-200">
                            <AlertTriangle className="w-3 h-3 text-amber-600" />
                            {p.conflict_count} Conflict{p.conflict_count > 1 ? 's' : ''}
                          </span>
                        ) : hasPending ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-sky-50 text-sky-800 border border-sky-200">
                            {p.pending_verifications_count} Pending Review
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-600">
                            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                            Verified
                          </span>
                        )}
                      </td>

                      {/* Action */}
                      <td className="py-3.5 px-4 text-right">
                        <span className="inline-flex items-center gap-1 text-xs font-semibold text-slate-500 group-hover:text-slate-900 transition-colors">
                          Open Profile
                          <ArrowRight className="w-3.5 h-3.5" />
                        </span>
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
