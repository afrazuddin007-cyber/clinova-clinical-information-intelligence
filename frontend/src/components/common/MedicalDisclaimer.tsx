import React from 'react';
import { ShieldAlert } from 'lucide-react';

export const MedicalDisclaimer: React.FC<{ compact?: boolean }> = ({ compact = false }) => {
  if (compact) {
    return (
      <div className="flex items-center gap-2 py-1 px-3 bg-amber-50/80 border-b border-amber-200 text-[11px] text-amber-800 font-medium">
        <ShieldAlert className="w-3.5 h-3.5 text-amber-600 shrink-0" />
        <span>Clinova is an information management & extraction platform, NOT a diagnostic or treatment tool. All medical insights require human physician review.</span>
      </div>
    );
  }

  return (
    <div className="p-3 bg-amber-50/90 border border-amber-200/80 rounded-lg text-xs text-amber-800 flex items-start gap-2.5 shadow-sm">
      <ShieldAlert className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" />
      <div>
        <span className="font-semibold block mb-0.5">Clinical Information Disclaimer:</span>
        Clinova transforms medical records into traceable, structured insights. It does not provide diagnoses, prescribe therapies, or make treatment recommendations. Every data point must be verified against original source documentation.
      </div>
    </div>
  );
};
