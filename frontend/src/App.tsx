import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from './context/AuthContext';
import { Patient, MedicalReport, ExtractedLabResult, Inconsistency } from './types';
import { patientApi, reportApi, clinicalApi, conflictApi, demoApi } from './services/api';

// Authentication
import { LoginModal } from './components/auth/LoginModal';

// Layout
import { Sidebar, NavigationSection } from './components/layout/Sidebar';

// Tier 1: Organization Workspace Views
import { PatientsListView } from './components/workspace/PatientsListView';
import { GlobalReportsView } from './components/workspace/GlobalReportsView';
import { GlobalVerificationView } from './components/workspace/GlobalVerificationView';
import { GlobalActivityView } from './components/workspace/GlobalActivityView';

// Tier 2: Dedicated Patient Profile Views
import { PatientProfileHeader } from './components/patient/PatientProfileHeader';
import { PatientOverviewTab } from './components/patient/PatientOverviewTab';
import { PatientRecordsTab } from './components/patient/PatientRecordsTab';
import { StructuredLabsTable } from './components/workspace/StructuredLabsTable';
import { ReportComparisonView } from './components/workspace/ReportComparisonView';
import { ConflictsBanner } from './components/workspace/ConflictsBanner';
import { VerificationQueue } from './components/workspace/VerificationQueue';
import { DoctorIntelligencePanel } from './components/intelligence/DoctorIntelligencePanel';

// Drawers & Modals
import { EvidenceDrawer } from './components/provenance/EvidenceDrawer';
import { ReportUploadModal } from './components/reports/ReportUploadModal';
import { PatientIntakeModal } from './components/patient/PatientIntakeModal';

// Icons
import {
  LayoutDashboard,
  FileText,
  TableProperties,
  GitCompare,
  AlertTriangle,
  CheckSquare,
  Sparkles,
  Activity
} from 'lucide-react';

export type ProfileTab =
  | 'OVERVIEW'
  | 'RECORDS'
  | 'LABS'
  | 'COMPARE'
  | 'CONFLICTS'
  | 'VERIFY'
  | 'ASSISTANT';

export const App: React.FC = () => {
  const { user, token, isLoading: isAuthLoading } = useAuth();

  // Organization Workspace State
  const [patients, setPatients] = useState<Patient[]>([]);
  const [currentSection, setCurrentSection] = useState<NavigationSection>('PATIENTS');

  // Active Patient Profile State (null = in organization directory/overview)
  const [activePatient, setActivePatient] = useState<Patient | null>(null);
  const activePatientRef = useRef<string | null>(null);
  const [activeProfileTab, setActiveProfileTab] = useState<ProfileTab>('OVERVIEW');

  // Active Patient Data
  const [reports, setReports] = useState<MedicalReport[]>([]);
  const [labs, setLabs] = useState<ExtractedLabResult[]>([]);
  const [conflicts, setConflicts] = useState<Inconsistency[]>([]);

  // Modals & Drawers
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isIntakeOpen, setIsIntakeOpen] = useState(false);
  const [isEditingIntake, setIsEditingIntake] = useState(false);
  const [evidenceDrawerTarget, setEvidenceDrawerTarget] = useState<ExtractedLabResult | null>(null);

  // Comparison selections
  const [compareReportA, setCompareReportA] = useState<string | undefined>();
  const [compareReportB, setCompareReportB] = useState<string | undefined>();

  // Async indicators
  const [isSeedingDemo, setIsSeedingDemo] = useState(false);
  const [isDataLoading, setIsDataLoading] = useState(false);

  // Load organization patients
  const loadPatients = async () => {
    try {
      const list = await patientApi.list();
      setPatients(list);
    } catch (err) {
      console.error('Failed to load patients', err);
    }
  };

  useEffect(() => {
    if (token) {
      loadPatients();
    }
  }, [token]);

  // Load active patient workspace records with strict patient isolation & race condition prevention
  const loadPatientWorkspace = async (patientId: string) => {
    setIsDataLoading(true);
    // Immediately clear previous patient state to avoid stale data flash
    setReports([]);
    setLabs([]);
    setConflicts([]);
    setEvidenceDrawerTarget(null);

    try {
      const [reps, labResults, conflictList] = await Promise.all([
        reportApi.list(patientId),
        clinicalApi.getLabs(patientId),
        conflictApi.getConflicts(patientId),
      ]);
      // Only commit if the user is still on this patient
      if (activePatientRef.current === patientId) {
        setReports(reps);
        setLabs(labResults);
        setConflicts(conflictList);
      }
    } catch (err) {
      console.error('Failed to load patient workspace', err);
    } finally {
      if (activePatientRef.current === patientId) {
        setIsDataLoading(false);
      }
    }
  };

  useEffect(() => {
    activePatientRef.current = activePatient?.id || null;
    if (activePatient) {
      loadPatientWorkspace(activePatient.id);
    } else {
      setReports([]);
      setLabs([]);
      setConflicts([]);
      setEvidenceDrawerTarget(null);
    }
  }, [activePatient]);

  // Seed demo case
  const handleLoadDemo = async () => {
    setIsSeedingDemo(true);
    try {
      await demoApi.seed();
      const list = await patientApi.list();
      setPatients(list);
      const demoPat = list.find((p) => p.patient_id === 'CL-8F29K4') || list[0];
      if (demoPat) {
        setActivePatient(demoPat);
        setActiveProfileTab('OVERVIEW');
      }
    } catch (err) {
      console.error('Failed to seed demo patient', err);
    } finally {
      setIsSeedingDemo(false);
    }
  };

  const totalPendingVerifications = patients.reduce(
    (acc, p) => acc + (p.pending_verifications_count || 0),
    0
  );

  if (isAuthLoading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center text-white text-xs">
        <Activity className="w-5 h-5 text-sky-400 animate-spin mr-2" />
        Initializing Clinova Clinical Session...
      </div>
    );
  }

  if (!token) {
    return <LoginModal />;
  }

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Persistent Left Sidebar */}
      <Sidebar
        currentSection={currentSection}
        onNavigate={(section) => {
          setCurrentSection(section);
          setActivePatient(null); // Return to organization level
        }}
        patientCount={patients.length}
        pendingVerificationCount={totalPendingVerifications}
        onNewPatientClick={() => {
          setIsEditingIntake(false);
          setIsIntakeOpen(true);
        }}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        {activePatient ? (
          /* ========================================================================= */
          /* TIER 2: DEDICATED PATIENT PROFILE WORKSPACE                              */
          /* ========================================================================= */
          <div className="flex-1 flex flex-col">
            {/* Sleek Profile Header */}
            <PatientProfileHeader
              patient={activePatient}
              onBack={() => {
                setActivePatient(null);
                setCurrentSection('PATIENTS');
                loadPatients();
              }}
              onUploadClick={() => setIsUploadOpen(true)}
              onEditClick={() => {
                setIsEditingIntake(true);
                setIsIntakeOpen(true);
              }}
            />

            {/* Profile Tab Navigation Strip */}
            <div className="bg-white border-b border-slate-200/90 px-6 sm:px-8">
              <div className="flex items-center gap-1 overflow-x-auto text-xs font-semibold py-1">
                {/* Overview */}
                <button
                  type="button"
                  onClick={() => setActiveProfileTab('OVERVIEW')}
                  className={`flex items-center gap-1.5 px-3 py-2 rounded-lg transition-colors whitespace-nowrap cursor-pointer ${
                    activeProfileTab === 'OVERVIEW'
                      ? 'text-slate-900 bg-slate-100 font-bold'
                      : 'text-slate-500 hover:text-slate-800 hover:bg-slate-50'
                  }`}
                >
                  <LayoutDashboard className="w-3.5 h-3.5" />
                  Overview
                </button>

                {/* Preserved Medical Records */}
                <button
                  type="button"
                  onClick={() => setActiveProfileTab('RECORDS')}
                  className={`flex items-center gap-1.5 px-3 py-2 rounded-lg transition-colors whitespace-nowrap cursor-pointer ${
                    activeProfileTab === 'RECORDS'
                      ? 'text-slate-900 bg-slate-100 font-bold'
                      : 'text-slate-500 hover:text-slate-800 hover:bg-slate-50'
                  }`}
                >
                  <FileText className="w-3.5 h-3.5" />
                  Medical Records ({reports.length})
                </button>

                {/* Structured Labs */}
                <button
                  type="button"
                  onClick={() => setActiveProfileTab('LABS')}
                  className={`flex items-center gap-1.5 px-3 py-2 rounded-lg transition-colors whitespace-nowrap cursor-pointer ${
                    activeProfileTab === 'LABS'
                      ? 'text-slate-900 bg-slate-100 font-bold'
                      : 'text-slate-500 hover:text-slate-800 hover:bg-slate-50'
                  }`}
                >
                  <TableProperties className="w-3.5 h-3.5" />
                  Structured Labs ({labs.length})
                </button>

                {/* Comparison Diff */}
                <button
                  type="button"
                  onClick={() => setActiveProfileTab('COMPARE')}
                  className={`flex items-center gap-1.5 px-3 py-2 rounded-lg transition-colors whitespace-nowrap cursor-pointer ${
                    activeProfileTab === 'COMPARE'
                      ? 'text-slate-900 bg-slate-100 font-bold'
                      : 'text-slate-500 hover:text-slate-800 hover:bg-slate-50'
                  }`}
                >
                  <GitCompare className="w-3.5 h-3.5" />
                  Compare Records
                </button>

                {/* Conflicts Banner */}
                <button
                  type="button"
                  onClick={() => setActiveProfileTab('CONFLICTS')}
                  className={`flex items-center gap-1.5 px-3 py-2 rounded-lg transition-colors whitespace-nowrap cursor-pointer ${
                    activeProfileTab === 'CONFLICTS'
                      ? 'text-slate-900 bg-slate-100 font-bold'
                      : 'text-slate-500 hover:text-slate-800 hover:bg-slate-50'
                  }`}
                >
                  <AlertTriangle className="w-3.5 h-3.5" />
                  Conflicts
                  {conflicts.filter((c) => c.resolution_status === 'FLAGGED').length > 0 && (
                    <span className="w-2 h-2 rounded-full bg-amber-500 ml-0.5" />
                  )}
                </button>

                {/* Verification Queue */}
                <button
                  type="button"
                  onClick={() => setActiveProfileTab('VERIFY')}
                  className={`flex items-center gap-1.5 px-3 py-2 rounded-lg transition-colors whitespace-nowrap cursor-pointer ${
                    activeProfileTab === 'VERIFY'
                      ? 'text-slate-900 bg-slate-100 font-bold'
                      : 'text-slate-500 hover:text-slate-800 hover:bg-slate-50'
                  }`}
                >
                  <CheckSquare className="w-3.5 h-3.5" />
                  Verification
                  {labs.filter((l) => l.verification_status === 'PENDING_VERIFICATION').length > 0 && (
                    <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-amber-100 text-amber-900 font-mono font-bold">
                      {labs.filter((l) => l.verification_status === 'PENDING_VERIFICATION').length}
                    </span>
                  )}
                </button>

                {/* Doctor Assistant */}
                <button
                  type="button"
                  onClick={() => setActiveProfileTab('ASSISTANT')}
                  className={`flex items-center gap-1.5 px-3 py-2 rounded-lg transition-colors whitespace-nowrap cursor-pointer ${
                    activeProfileTab === 'ASSISTANT'
                      ? 'text-slate-900 bg-slate-100 font-bold'
                      : 'text-slate-500 hover:text-slate-800 hover:bg-slate-50'
                  }`}
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  Doctor Assistant
                </button>
              </div>
            </div>

            {/* Profile Tab Contents */}
            <main className="flex-1 p-6 sm:p-8">
              {activeProfileTab === 'OVERVIEW' && (
                <PatientOverviewTab
                  key={activePatient.id}
                  patient={activePatient}
                  reports={reports}
                  labs={labs}
                  conflicts={conflicts}
                  onUploadClick={() => setIsUploadOpen(true)}
                  onNavigateToTab={(tab) => setActiveProfileTab(tab as ProfileTab)}
                />
              )}

              {activeProfileTab === 'RECORDS' && (
                <PatientRecordsTab
                  key={activePatient.id}
                  patient={activePatient}
                  reports={reports}
                  labs={labs}
                  onUploadClick={() => setIsUploadOpen(true)}
                  onCompareClick={(repA, repB) => {
                    setCompareReportA(repA);
                    setCompareReportB(repB);
                    setActiveProfileTab('COMPARE');
                  }}
                  onInspectProvenance={(lab) => setEvidenceDrawerTarget(lab)}
                />
              )}

              {activeProfileTab === 'LABS' && (
                <div className="max-w-5xl mx-auto">
                  <StructuredLabsTable
                    key={activePatient.id}
                    labs={labs}
                    onInspectProvenance={(lab) => setEvidenceDrawerTarget(lab)}
                    onVerifyClick={() => setActiveProfileTab('VERIFY')}
                  />
                </div>
              )}

              {activeProfileTab === 'COMPARE' && (
                <div className="max-w-5xl mx-auto">
                  <ReportComparisonView
                    key={activePatient.id}
                    patientId={activePatient.id}
                    reports={reports}
                    initialReportAId={compareReportA}
                    initialReportBId={compareReportB}
                  />
                </div>
              )}

              {activeProfileTab === 'CONFLICTS' && (
                <div className="max-w-5xl mx-auto">
                  <ConflictsBanner
                    key={activePatient.id}
                    conflicts={conflicts}
                    onConflictUpdated={() => loadPatientWorkspace(activePatient.id)}
                  />
                </div>
              )}

              {activeProfileTab === 'VERIFY' && (
                <div className="max-w-5xl mx-auto">
                  <VerificationQueue
                    key={activePatient.id}
                    labs={labs}
                    onItemUpdated={() => {
                      loadPatientWorkspace(activePatient.id);
                      loadPatients();
                    }}
                    onInspectProvenance={(lab) => setEvidenceDrawerTarget(lab)}
                  />
                </div>
              )}

              {activeProfileTab === 'ASSISTANT' && (
                <div className="max-w-4xl mx-auto">
                  <DoctorIntelligencePanel key={activePatient.id} patientId={activePatient.id} />
                </div>
              )}
            </main>
          </div>
        ) : (
          /* ========================================================================= */
          /* TIER 1: ORGANIZATION WORKSPACE LEVEL VIEWS                                */
          /* ========================================================================= */
          <main className="flex-1 p-6 sm:p-8">
            {currentSection === 'PATIENTS' && (
              <PatientsListView
                patients={patients}
                onSelectPatient={(p) => {
                  setActivePatient(p);
                  setActiveProfileTab('OVERVIEW');
                }}
                onNewPatientClick={() => {
                  setIsEditingIntake(false);
                  setIsIntakeOpen(true);
                }}
                onLoadDemo={handleLoadDemo}
                isSeedingDemo={isSeedingDemo}
              />
            )}

            {currentSection === 'ALL_REPORTS' && (
              <GlobalReportsView
                patients={patients}
                onSelectPatient={(p, tab) => {
                  setActivePatient(p);
                  setActiveProfileTab((tab as ProfileTab) || 'RECORDS');
                }}
              />
            )}

            {currentSection === 'GLOBAL_VERIFICATION' && (
              <GlobalVerificationView
                patients={patients}
                onSelectPatient={(p, tab) => {
                  setActivePatient(p);
                  setActiveProfileTab((tab as ProfileTab) || 'VERIFY');
                }}
                onInspectProvenance={(lab) => setEvidenceDrawerTarget(lab)}
                onQueueChanged={() => loadPatients()}
              />
            )}

            {currentSection === 'ACTIVITY' && (
              <GlobalActivityView
                patients={patients}
                onSelectPatient={(p) => {
                  setActivePatient(p);
                  setActiveProfileTab('OVERVIEW');
                }}
              />
            )}
          </main>
        )}
      </div>

      {/* Global Slide-Over Evidence Drawer */}
      <EvidenceDrawer
        isOpen={Boolean(evidenceDrawerTarget)}
        onClose={() => setEvidenceDrawerTarget(null)}
        lab={evidenceDrawerTarget}
      />

      {/* Report Upload Modal */}
      {activePatient && (
        <ReportUploadModal
          isOpen={isUploadOpen}
          onClose={() => setIsUploadOpen(false)}
          patientId={activePatient.id}
          onUploadSuccess={() => {
            loadPatientWorkspace(activePatient.id);
            loadPatients();
          }}
        />
      )}

      {/* Patient Intake Modal (Create / Edit) */}
      <PatientIntakeModal
        isOpen={isIntakeOpen}
        onClose={() => setIsIntakeOpen(false)}
        initialPatient={isEditingIntake ? activePatient : null}
        onPatientCreatedOrUpdated={(p) => {
          loadPatients();
          setActivePatient(p);
          setActiveProfileTab('OVERVIEW');
        }}
      />
    </div>
  );
};
