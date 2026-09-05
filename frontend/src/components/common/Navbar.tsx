import React, { useState } from 'react';
import { Patient } from '../../types';
import { useAuth } from '../../context/AuthContext';
import { MedicalDisclaimer } from './MedicalDisclaimer';
import { Activity, Plus, Database, User, LogOut, ChevronDown, Check } from 'lucide-react';

interface NavbarProps {
  patients: Patient[];
  activePatient: Patient | null;
  onSelectPatient: (p: Patient) => void;
  onOpenNewPatient: () => void;
  onLoadDemo: () => void;
  isSeedingDemo: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  patients,
  activePatient,
  onSelectPatient,
  onOpenNewPatient,
  onLoadDemo,
  isSeedingDemo,
}) => {
  const { user, logout } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 bg-white border-b border-slate-200 shadow-sm">
      <MedicalDisclaimer compact />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-sky-600 flex items-center justify-center text-white shadow-sm ring-1 ring-sky-700/20">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold tracking-tight text-slate-900">CLINOVA</span>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-sky-100 text-sky-800 uppercase tracking-wider">
                Clinical Intelligence
              </span>
            </div>
            <p className="text-[11px] text-slate-500 font-medium hidden sm:block">
              One patient. One record. Every insight traceable.
            </p>
          </div>
        </div>

        {/* Patient Switcher */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="flex items-center gap-2.5 px-3.5 py-1.5 rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100/80 text-sm font-medium text-slate-800 transition-colors shadow-xs"
          >
            <div className="w-2 h-2 rounded-full bg-emerald-500" />
            <span className="max-w-[140px] truncate">
              {activePatient ? `${activePatient.full_name} (${activePatient.patient_id})` : 'Select Patient'}
            </span>
            <ChevronDown className="w-4 h-4 text-slate-500 ml-1" />
          </button>

          {dropdownOpen && (
            <div className="absolute left-0 mt-2 w-72 rounded-xl bg-white border border-slate-200 shadow-xl py-2 z-50 animate-in fade-in zoom-in-95 duration-100">
              <div className="px-3 py-1.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Authorized Patients ({patients.length})
              </div>
              <div className="max-h-60 overflow-y-auto divide-y divide-slate-100">
                {patients.length === 0 ? (
                  <div className="px-4 py-3 text-xs text-slate-500 text-center">No patients found. Create one or load demo.</div>
                ) : (
                  patients.map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => {
                        onSelectPatient(p);
                        setDropdownOpen(false);
                      }}
                      className="w-full text-left px-3 py-2 text-xs flex items-center justify-between hover:bg-sky-50/70 transition-colors"
                    >
                      <div>
                        <div className="font-semibold text-slate-800">{p.full_name}</div>
                        <div className="text-[11px] text-slate-500 font-mono">{p.patient_id} • {p.age}y {p.sex}</div>
                      </div>
                      {activePatient?.id === p.id && <Check className="w-4 h-4 text-sky-600" />}
                    </button>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2.5">
          {/* Load Demo Patient */}
          <button
            type="button"
            onClick={onLoadDemo}
            disabled={isSeedingDemo}
            className="hidden md:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-teal-300 bg-teal-50 hover:bg-teal-100/80 text-teal-800 text-xs font-semibold shadow-xs transition-colors cursor-pointer"
            title="Populates Eleanor Vance (CL-8F29K4) with 2 reports, longitudinal diffs, conflicts, and pending verifications."
          >
            <Database className="w-3.5 h-3.5 text-teal-700" />
            {isSeedingDemo ? 'Loading Demo...' : 'Load Demo Patient'}
          </button>

          {/* New Patient Button */}
          <button
            type="button"
            onClick={onOpenNewPatient}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-700 text-white text-xs font-semibold shadow-sm transition-colors cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            New Patient
          </button>

          {/* Clinician Profile */}
          <div className="h-6 w-px bg-slate-200 mx-1 hidden sm:block" />

          <div className="flex items-center gap-2">
            <div className="hidden lg:block text-right">
              <div className="text-xs font-semibold text-slate-900">{user?.full_name || 'Dr. Clinician'}</div>
              <div className="text-[10px] text-slate-500 capitalize">{user?.role || 'Doctor'}</div>
            </div>
            <button
              type="button"
              onClick={logout}
              className="p-1.5 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors"
              title="Sign Out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
