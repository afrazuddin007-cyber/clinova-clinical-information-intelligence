import React from 'react';
import { useAuth } from '../../context/AuthContext';
import {
  Users,
  FileText,
  CheckSquare,
  Activity,
  LogOut,
  Building2,
  ChevronRight,
  ShieldCheck,
  Plus
} from 'lucide-react';

export type NavigationSection = 'PATIENTS' | 'ALL_REPORTS' | 'GLOBAL_VERIFICATION' | 'ACTIVITY';

interface SidebarProps {
  currentSection: NavigationSection;
  onNavigate: (section: NavigationSection) => void;
  patientCount: number;
  pendingVerificationCount: number;
  onNewPatientClick: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentSection,
  onNavigate,
  patientCount,
  pendingVerificationCount,
  onNewPatientClick,
}) => {
  const { user, logout } = useAuth();
  const orgName = user?.organization_name || 'MVSR Medical Center';

  return (
    <aside className="w-64 bg-white border-r border-slate-200/90 flex flex-col justify-between shrink-0 h-screen sticky top-0 select-none">
      {/* Top Organization Header */}
      <div>
        <div className="p-4 border-b border-slate-100 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-slate-900 text-white flex items-center justify-center font-bold text-sm tracking-tight shadow-xs">
            C
          </div>
          <div className="overflow-hidden">
            <div className="text-xs font-bold text-slate-900 truncate tracking-tight">{orgName}</div>
            <div className="text-[11px] text-slate-400 flex items-center gap-1 font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              Clinova Workspace
            </div>
          </div>
        </div>

        {/* Primary CTA: New Patient */}
        <div className="p-3">
          <button
            type="button"
            onClick={onNewPatientClick}
            className="w-full flex items-center justify-center gap-2 py-2 px-3 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg transition-colors shadow-2xs cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            New Patient
          </button>
        </div>

        {/* Navigation Items */}
        <nav className="px-2 space-y-0.5 text-xs font-medium">
          <button
            type="button"
            onClick={() => onNavigate('PATIENTS')}
            className={`w-full flex items-center justify-between px-3 py-2 rounded-lg transition-colors cursor-pointer ${
              currentSection === 'PATIENTS'
                ? 'bg-slate-100 text-slate-900 font-semibold'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
            }`}
          >
            <div className="flex items-center gap-2.5">
              <Users className={`w-4 h-4 ${currentSection === 'PATIENTS' ? 'text-slate-900' : 'text-slate-400'}`} />
              <span>Patients</span>
            </div>
            {patientCount > 0 && (
              <span className="text-[11px] px-1.5 py-0.2 rounded font-mono text-slate-500 bg-slate-200/60">
                {patientCount}
              </span>
            )}
          </button>

          <button
            type="button"
            onClick={() => onNavigate('ALL_REPORTS')}
            className={`w-full flex items-center justify-between px-3 py-2 rounded-lg transition-colors cursor-pointer ${
              currentSection === 'ALL_REPORTS'
                ? 'bg-slate-100 text-slate-900 font-semibold'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
            }`}
          >
            <div className="flex items-center gap-2.5">
              <FileText className={`w-4 h-4 ${currentSection === 'ALL_REPORTS' ? 'text-slate-900' : 'text-slate-400'}`} />
              <span>Medical Records</span>
            </div>
          </button>

          <button
            type="button"
            onClick={() => onNavigate('GLOBAL_VERIFICATION')}
            className={`w-full flex items-center justify-between px-3 py-2 rounded-lg transition-colors cursor-pointer ${
              currentSection === 'GLOBAL_VERIFICATION'
                ? 'bg-slate-100 text-slate-900 font-semibold'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
            }`}
          >
            <div className="flex items-center gap-2.5">
              <CheckSquare className={`w-4 h-4 ${currentSection === 'GLOBAL_VERIFICATION' ? 'text-slate-900' : 'text-slate-400'}`} />
              <span>Verification Queue</span>
            </div>
            {pendingVerificationCount > 0 && (
              <span className="text-[10px] px-1.5 py-0.2 rounded-full font-mono font-bold text-amber-800 bg-amber-100">
                {pendingVerificationCount}
              </span>
            )}
          </button>

          <button
            type="button"
            onClick={() => onNavigate('ACTIVITY')}
            className={`w-full flex items-center justify-between px-3 py-2 rounded-lg transition-colors cursor-pointer ${
              currentSection === 'ACTIVITY'
                ? 'bg-slate-100 text-slate-900 font-semibold'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
            }`}
          >
            <div className="flex items-center gap-2.5">
              <Activity className={`w-4 h-4 ${currentSection === 'ACTIVITY' ? 'text-slate-900' : 'text-slate-400'}`} />
              <span>Activity Log</span>
            </div>
          </button>
        </nav>
      </div>

      {/* Bottom Profile / User Controls */}
      <div className="p-3 border-t border-slate-100">
        <div className="p-2 rounded-lg bg-slate-50/70 border border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="w-7 h-7 rounded-full bg-slate-200 text-slate-700 flex items-center justify-center font-bold text-xs shrink-0">
              {user?.full_name?.charAt(0) || 'D'}
            </div>
            <div className="overflow-hidden">
              <div className="text-xs font-semibold text-slate-800 truncate">{user?.full_name || 'Clinician'}</div>
              <div className="text-[10px] text-slate-400 capitalize">{user?.role || 'Physician'}</div>
            </div>
          </div>
          <button
            type="button"
            onClick={logout}
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 rounded-md transition-colors cursor-pointer"
            title="Sign Out"
          >
            <LogOut className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </aside>
  );
};
