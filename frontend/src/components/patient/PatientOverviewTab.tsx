import React, { useState, useEffect } from 'react';
import { Patient, MedicalReport, ExtractedLabResult, Inconsistency } from '../../types';
import { patientApi } from '../../services/api';
import {
  UploadCloud,
  FileText,
  AlertTriangle,
  CheckCircle2,
  Calendar,
  Sparkles,
  Pill,
  HeartPulse,
  Stethoscope,
  Clock,
  ArrowRight,
  ShieldAlert,
  ShieldCheck,
  Cpu,
  Layers
} from 'lucide-react';

interface PatientOverviewTabProps {
  patient: Patient;
  reports: MedicalReport[];
  labs: ExtractedLabResult[];
  conflicts: Inconsistency[];
  onUploadClick: () => void;
  onNavigateToTab: (tab: string) => void;
}

export const PatientOverviewTab: React.FC<PatientOverviewTabProps> = ({
  patient,
  reports,
  labs,
  conflicts,
  onUploadClick,
  onNavigateToTab,
}) => {
  const [summary, setSummary] = useState<string | null>(null);
  const [summaryGroundedCount, setSummaryGroundedCount] = useState<number>(0);
  const [loadingSummary, setLoadingSummary] = useState(false);

  useEffect(() => {
    let isCurrent = true;
    const fetchSummary = async () => {
      setLoadingSummary(true);
      try {
        const res = await patientApi.getSummary(patient.id);
        if (isCurrent) {
          setSummary(res.summary);
          setSummaryGroundedCount(res.grounded_record_count);
        }
      } catch (err) {
        console.error('Failed to load patient summary', err);
      } finally {
        if (isCurrent) {
          setLoadingSummary(false);
        }
      }
    };
    fetchSummary();
    return () => {
      isCurrent = false;
    };
  }, [patient.id]);

  const latestReport = reports[0];
  const pendingLabsCount = labs.filter((l) => l.verification_status === 'PENDING_VERIFICATION').length;
  const verifiedLabsCount = labs.filter((l) => l.verification_status === 'HUMAN_VERIFIED').length;
  const activeConflictsCount = conflicts.filter((c) => c.resolution_status === 'FLAGGED').length;

  // 0-Report Experience: Hero Dropzone
  if (reports.length === 0) {
    return (
      <div className="max-w-3xl mx-auto py-8">
        <div className="bg-white rounded-2xl border border-slate-200 shadow-2xs p-8 text-center">
          <div className="w-14 h-14 rounded-2xl bg-slate-900 text-white flex items-center justify-center mx-auto mb-4 shadow-sm">
            <UploadCloud className="w-7 h-7" />
          </div>

          <h2 className="text-lg font-bold text-slate-900 tracking-tight mb-1">
            Upload Medical Record for {patient.full_name}
          </h2>
          <p className="text-xs text-slate-500 max-w-md mx-auto mb-6">
            Upload laboratory panels, clinical summaries, or diagnostic reports. Clinova will extract structured parameters, evaluate source reference ranges, and establish traceable provenance.
          </p>

          <div
            onClick={onUploadClick}
            className="border-2 border-dashed border-slate-300 hover:border-slate-400 bg-slate-50/50 hover:bg-slate-50 rounded-xl p-10 cursor-pointer transition-colors max-w-lg mx-auto focus:outline-none focus:ring-2 focus:ring-sky-500/20"
            tabIndex={0}
            role="button"
            aria-label="Upload first medical record"
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onUploadClick();
              }
            }}
          >
            <div className="text-xs font-semibold text-slate-800 mb-1">
              Click to select medical report, or drag and drop here
            </div>
            <p className="text-[11px] text-slate-400">
              Supported formats: PDF, PNG, JPEG • Max file size: 10 MB
            </p>
          </div>

          <div className="mt-8 pt-6 border-t border-slate-100 flex items-center justify-center gap-6 text-[11px] text-slate-500 font-medium">
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
              Source Preserved
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
              Reference-Range Aware
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
              Zero Hallucination
            </span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5 max-w-5xl mx-auto">
      {/* Top Clinical Status Overview Strip (3 Cards) */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
        {/* Card 1: Latest Medical Record */}
        <div
          onClick={() => onNavigateToTab('RECORDS')}
          className="bg-white p-4 rounded-2xl border border-slate-200/90 shadow-2xs hover:border-sky-300 hover:shadow-xs transition-all cursor-pointer group"
          role="button"
          tabIndex={0}
          onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onNavigateToTab('RECORDS')}
          aria-label="View medical records"
        >
          <div className="flex items-center justify-between text-[11px] text-slate-500 font-medium mb-1.5">
            <span className="font-bold tracking-wider uppercase text-[10px]">Latest Medical Record</span>
            <FileText className="w-3.5 h-3.5 text-slate-400 group-hover:text-sky-600 transition-colors" />
          </div>
          <div className="text-sm font-bold text-slate-900 truncate group-hover:text-sky-700 transition-colors">
            {latestReport?.original_file_name || 'No reports uploaded'}
          </div>
          <div className="text-[11px] text-slate-500 mt-1.5 flex items-center justify-between">
            <span className="flex items-center gap-1 font-mono">
              <Calendar className="w-3 h-3 text-slate-400" />
              {latestReport?.report_date ? new Date(latestReport.report_date).toLocaleDateString() : 'Recent Upload'}
            </span>
            <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-1.5 py-0.2 rounded">
              EXTRACTED
            </span>
          </div>
        </div>

        {/* Card 2: Verification Status */}
        <div
          onClick={() => onNavigateToTab('VERIFY')}
          className="bg-white p-4 rounded-2xl border border-slate-200/90 shadow-2xs hover:border-sky-300 hover:shadow-xs transition-all cursor-pointer group"
          role="button"
          tabIndex={0}
          onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onNavigateToTab('VERIFY')}
          aria-label="View verification queue"
        >
          <div className="flex items-center justify-between text-[11px] text-slate-500 font-medium mb-1.5">
            <span className="font-bold tracking-wider uppercase text-[10px]">Verification Status</span>
            <CheckCircle2 className="w-3.5 h-3.5 text-slate-400 group-hover:text-emerald-600 transition-colors" />
          </div>
          <div className="text-sm font-bold text-slate-900">
            {pendingLabsCount > 0 ? (
              <span className="text-amber-800 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
                {pendingLabsCount} Finding{pendingLabsCount > 1 ? 's' : ''} Pending Review
              </span>
            ) : (
              <span className="text-emerald-700 flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                All Findings Verified
              </span>
            )}
          </div>
          <div className="text-[11px] text-slate-500 mt-1.5 flex items-center justify-between">
            <span>{pendingLabsCount > 0 ? 'Requires clinician confirmation' : 'Clinician audited & confirmed'}</span>
            <span className="text-[10px] font-mono text-slate-600 bg-slate-100 px-1.5 py-0.2 rounded">
              {verifiedLabsCount}/{labs.length} verified
            </span>
          </div>
        </div>

        {/* Card 3: Cross-Record Reconciliation */}
        <div
          onClick={() => onNavigateToTab('CONFLICTS')}
          className="bg-white p-4 rounded-2xl border border-slate-200/90 shadow-2xs hover:border-sky-300 hover:shadow-xs transition-all cursor-pointer group"
          role="button"
          tabIndex={0}
          onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onNavigateToTab('CONFLICTS')}
          aria-label="View cross-record inconsistencies"
        >
          <div className="flex items-center justify-between text-[11px] text-slate-500 font-medium mb-1.5">
            <span className="font-bold tracking-wider uppercase text-[10px]">Cross-Record Reconciliation</span>
            <AlertTriangle className="w-3.5 h-3.5 text-slate-400 group-hover:text-amber-600 transition-colors" />
          </div>
          <div className="text-sm font-bold text-slate-900">
            {activeConflictsCount > 0 ? (
              <span className="text-amber-800 flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                {activeConflictsCount} Conflict{activeConflictsCount > 1 ? 's' : ''} Flagged
              </span>
            ) : (
              <span className="text-slate-800 flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                0 Discrepancies
              </span>
            )}
          </div>
          <div className="text-[11px] text-slate-500 mt-1.5 flex items-center justify-between">
            <span>{activeConflictsCount > 0 ? 'Requires physician resolution' : 'Records completely consistent'}</span>
            <span className={`text-[10px] font-semibold px-1.5 py-0.2 rounded ${activeConflictsCount > 0 ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-600'}`}>
              {activeConflictsCount > 0 ? 'REVIEW' : 'STABLE'}
            </span>
          </div>
        </div>
      </div>

      {/* Longitudinal AI Summary Card */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-2xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-slate-900">Longitudinal Record Summary</span>
            <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-purple-50 text-purple-700 border border-purple-200 inline-flex items-center gap-1">
              <Cpu className="w-3 h-3 text-purple-600" />
              AI_SYNTHESIS (DERIVED) • Grounded in {summaryGroundedCount} verified findings
            </span>
          </div>
          <span className="text-[10px] font-bold text-slate-500 bg-slate-100 border border-slate-200 px-2 py-0.5 rounded-full self-start sm:self-auto flex items-center gap-1">
            <ShieldAlert className="w-3 h-3 text-slate-500" />
            Non-Diagnostic
          </span>
        </div>

        {loadingSummary ? (
          <div className="py-6 text-xs text-slate-400 animate-pulse text-center">
            Synthesizing clinical findings across verified records...
          </div>
        ) : summary ? (
          <div>
            <div className="text-xs text-slate-800 leading-relaxed bg-slate-50/80 p-4 rounded-xl border border-slate-200/80 font-normal">
              {summary}
            </div>
            <div className="mt-2 text-[10px] text-slate-400 italic flex items-center gap-1">
              <span>Grounding Standard: Clinova organizes explicitly documented records. It never invents diagnoses, clinical facts, or dosage recommendations.</span>
            </div>
          </div>
        ) : (
          <div className="text-xs text-slate-400 py-3 text-center">No structured summary available.</div>
        )}
      </div>

      {/* Documented Intake Information Card (USER_PROVIDED) */}
      <div className="bg-white rounded-2xl border border-slate-200/90 shadow-2xs overflow-hidden">
        <div className="p-4 border-b border-slate-100 bg-slate-50/60 flex items-center justify-between">
          <div>
            <h3 className="text-xs font-bold text-slate-900">Clinical Intake Snapshot</h3>
            <p className="text-[11px] text-slate-500 mt-0.5">Information provided manually during patient intake registration</p>
          </div>
          <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-slate-200 text-slate-700 border border-slate-300">
            [USER_PROVIDED (INTAKE)]
          </span>
        </div>

        <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-3.5 text-xs">
          {/* Allergies */}
          <div className="p-3.5 rounded-xl bg-slate-50/70 border border-slate-200/80">
            <span className="text-[11px] font-bold text-slate-700 flex items-center gap-1.5 mb-1">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
              Documented Allergies
            </span>
            <p className="text-slate-900 font-semibold pl-5">{patient.allergies || 'None documented'}</p>
          </div>

          {/* Current Medications */}
          <div className="p-3.5 rounded-xl bg-slate-50/70 border border-slate-200/80">
            <span className="text-[11px] font-bold text-slate-700 flex items-center gap-1.5 mb-1">
              <Pill className="w-3.5 h-3.5 text-sky-600" />
              Current Medications
            </span>
            <p className="text-slate-900 font-semibold pl-5">{patient.current_medications || 'None documented'}</p>
          </div>

          {/* Existing Conditions */}
          <div className="p-3.5 rounded-xl bg-slate-50/70 border border-slate-200/80">
            <span className="text-[11px] font-bold text-slate-700 flex items-center gap-1.5 mb-1">
              <HeartPulse className="w-3.5 h-3.5 text-slate-700" />
              Existing Conditions
            </span>
            <p className="text-slate-900 font-semibold pl-5">{patient.existing_conditions || 'None documented'}</p>
          </div>

          {/* Symptoms */}
          <div className="p-3.5 rounded-xl bg-slate-50/70 border border-slate-200/80">
            <span className="text-[11px] font-bold text-slate-700 flex items-center gap-1.5 mb-1">
              <Stethoscope className="w-3.5 h-3.5 text-slate-700" />
              Active Symptoms
            </span>
            <p className="text-slate-900 font-semibold pl-5">{patient.symptoms || 'None recorded'}</p>
          </div>
        </div>
      </div>
    </div>
  );
};
