import React from 'react';
import { Patient } from '../../types';
import { ArrowLeft, UploadCloud, Edit2 } from 'lucide-react';

interface PatientProfileHeaderProps {
  patient: Patient;
  onBack: () => void;
  onUploadClick: () => void;
  onEditClick: () => void;
}

export const PatientProfileHeader: React.FC<PatientProfileHeaderProps> = ({
  patient,
  onBack,
  onUploadClick,
  onEditClick,
}) => {
  return (
    <div className="bg-white border-b border-slate-200/90 py-4 px-6 sm:px-8">
      {/* Breadcrumb */}
      <div className="mb-3">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-slate-900 transition-colors cursor-pointer"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Patients Directory
        </button>
      </div>

      {/* Main Header Info */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">{patient.full_name}</h1>
            <span className="px-2 py-0.5 rounded font-mono text-xs font-semibold bg-slate-100 text-slate-800 border border-slate-200">
              {patient.patient_id}
            </span>
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-500 mt-1">
            <span>{patient.age} years old</span>
            <span>•</span>
            <span className="capitalize">{patient.sex}</span>
            <span>•</span>
            <span>{patient.report_count} Medical Report{patient.report_count !== 1 ? 's' : ''} on file</span>
          </div>
        </div>

        {/* Primary Action Buttons */}
        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={onEditClick}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 rounded-lg shadow-2xs transition-colors cursor-pointer"
          >
            <Edit2 className="w-3.5 h-3.5 text-slate-400" />
            Edit Patient Details
          </button>

          <button
            type="button"
            onClick={onUploadClick}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg shadow-xs transition-colors cursor-pointer"
          >
            <UploadCloud className="w-3.5 h-3.5" />
            Upload Medical Record
          </button>
        </div>
      </div>
    </div>
  );
};
