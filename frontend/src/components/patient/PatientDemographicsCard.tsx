import React from 'react';
import { Patient } from '../../types';
import { ProvenanceBadge } from '../common/ProvenanceBadge';
import { User, AlertCircle, Pill, HeartPulse, Stethoscope, Edit2 } from 'lucide-react';

interface PatientDemographicsCardProps {
  patient: Patient;
  onEditIntake: () => void;
}

export const PatientDemographicsCard: React.FC<PatientDemographicsCardProps> = ({
  patient,
  onEditIntake,
}) => {
  return (
    <div className="bg-white rounded-xl border border-slate-200/90 shadow-xs overflow-hidden">
      {/* Header with Patient ID */}
      <div className="p-4 bg-gradient-to-r from-slate-900 to-slate-800 text-white flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2 py-0.5 rounded font-mono text-xs font-bold bg-sky-500/20 text-sky-300 border border-sky-400/30">
              {patient.patient_id}
            </span>
            <ProvenanceBadge provenance="USER_PROVIDED" />
          </div>
          <h2 className="text-lg font-bold tracking-tight">{patient.full_name}</h2>
          <p className="text-xs text-slate-300">
            {patient.age} years old • <span className="capitalize">{patient.sex}</span>
          </p>
        </div>
        <button
          type="button"
          onClick={onEditIntake}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-xs font-medium text-white transition-colors cursor-pointer"
        >
          <Edit2 className="w-3.5 h-3.5" />
          Edit Intake
        </button>
      </div>

      {/* Structured Clinical Intake Grid */}
      <div className="p-4 space-y-3.5 text-xs">
        {/* Allergies */}
        <div className="rounded-lg bg-rose-50/50 p-2.5 border border-rose-100">
          <div className="flex items-center justify-between mb-1">
            <span className="font-semibold text-rose-900 flex items-center gap-1.5">
              <AlertCircle className="w-3.5 h-3.5 text-rose-600" />
              Documented Allergies
            </span>
            <span className="text-[10px] text-rose-500 font-medium">[USER_PROVIDED]</span>
          </div>
          <p className="text-slate-700 font-medium pl-5">{patient.allergies || 'None documented'}</p>
        </div>

        {/* Current Medications */}
        <div className="rounded-lg bg-sky-50/50 p-2.5 border border-sky-100">
          <div className="flex items-center justify-between mb-1">
            <span className="font-semibold text-sky-900 flex items-center gap-1.5">
              <Pill className="w-3.5 h-3.5 text-sky-600" />
              Current Medications
            </span>
            <span className="text-[10px] text-sky-500 font-medium">[USER_PROVIDED]</span>
          </div>
          <p className="text-slate-700 font-medium pl-5">{patient.current_medications || 'None documented'}</p>
        </div>

        {/* Existing Conditions */}
        <div className="rounded-lg bg-slate-50 p-2.5 border border-slate-200/80">
          <div className="flex items-center justify-between mb-1">
            <span className="font-semibold text-slate-800 flex items-center gap-1.5">
              <HeartPulse className="w-3.5 h-3.5 text-slate-600" />
              Existing Conditions
            </span>
            <span className="text-[10px] text-slate-500 font-medium">[USER_PROVIDED]</span>
          </div>
          <p className="text-slate-700 font-medium pl-5">{patient.existing_conditions || 'None documented'}</p>
        </div>

        {/* Active Symptoms */}
        <div className="rounded-lg bg-slate-50 p-2.5 border border-slate-200/80">
          <div className="flex items-center justify-between mb-1">
            <span className="font-semibold text-slate-800 flex items-center gap-1.5">
              <Stethoscope className="w-3.5 h-3.5 text-slate-600" />
              Reported Symptoms
            </span>
            <span className="text-[10px] text-slate-500 font-medium">[USER_PROVIDED]</span>
          </div>
          <p className="text-slate-700 font-medium pl-5">{patient.symptoms || 'None reported'}</p>
        </div>
      </div>
    </div>
  );
};
