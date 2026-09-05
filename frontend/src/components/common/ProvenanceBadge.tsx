import React from 'react';
import { ProvenanceType, VerificationStatus } from '../../types';
import { Sparkles, UserCheck, User, Cpu, XCircle } from 'lucide-react';

interface ProvenanceBadgeProps {
  provenance: ProvenanceType;
  verificationStatus?: VerificationStatus;
  onClick?: () => void;
  className?: string;
}

export const ProvenanceBadge: React.FC<ProvenanceBadgeProps> = ({
  provenance,
  verificationStatus,
  onClick,
  className = ''
}) => {
  const isClickable = Boolean(onClick);

  // 1. REJECTED
  if (verificationStatus === 'REJECTED') {
    return (
      <button
        type="button"
        onClick={onClick}
        disabled={!isClickable}
        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-rose-50 text-rose-700 border border-rose-200 ${isClickable ? 'hover:bg-rose-100 cursor-pointer focus:ring-2 focus:ring-rose-500/20 focus:outline-none' : 'cursor-default'} ${className}`}
        title="Excluded from active clinical records by clinician"
        aria-label="Status: Rejected"
      >
        <XCircle className="w-3 h-3 text-rose-600" />
        <span>REJECTED</span>
      </button>
    );
  }

  // 2. VERIFIED (Human Verified)
  if (verificationStatus === 'HUMAN_VERIFIED' || provenance === 'HUMAN_VERIFIED') {
    return (
      <button
        type="button"
        onClick={onClick}
        disabled={!isClickable}
        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200 shadow-2xs ${isClickable ? 'hover:bg-emerald-100 cursor-pointer focus:ring-2 focus:ring-emerald-500/20 focus:outline-none' : 'cursor-default'} ${className}`}
        title="Audited and confirmed by a licensed clinician"
        aria-label="Status: Verified by clinician"
      >
        <UserCheck className="w-3 h-3 text-emerald-700" />
        <span>VERIFIED</span>
      </button>
    );
  }

  // 3. USER_PROVIDED (Intake)
  if (provenance === 'USER_PROVIDED') {
    return (
      <button
        type="button"
        onClick={onClick}
        disabled={!isClickable}
        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200 ${isClickable ? 'hover:bg-slate-200 cursor-pointer focus:ring-2 focus:ring-slate-400/20 focus:outline-none' : 'cursor-default'} ${className}`}
        title="Documented manually during patient registration"
        aria-label="Status: User provided intake"
      >
        <User className="w-3 h-3 text-slate-600" />
        <span>USER_PROVIDED (INTAKE)</span>
      </button>
    );
  }

  // 4. AI_GENERATED / AI_SYNTHESIS
  if (provenance === 'AI_GENERATED') {
    return (
      <button
        type="button"
        onClick={onClick}
        disabled={!isClickable}
        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-purple-50 text-purple-700 border border-purple-200 ${isClickable ? 'hover:bg-purple-100 cursor-pointer focus:ring-2 focus:ring-purple-500/20 focus:outline-none' : 'cursor-default'} ${className}`}
        title="Synthesized by AI from verified structured patient records"
        aria-label="Status: AI Synthesized derived information"
      >
        <Cpu className="w-3 h-3 text-purple-600" />
        <span>AI_SYNTHESIS (DERIVED)</span>
      </button>
    );
  }

  // 5. EXTRACTED (PENDING REVIEW)
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!isClickable}
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-50 text-amber-800 border border-amber-200 shadow-2xs ${isClickable ? 'hover:bg-amber-100 cursor-pointer focus:ring-2 focus:ring-amber-500/20 focus:outline-none' : 'cursor-default'} ${className}`}
      title="Extracted from source document by AI; awaiting clinician review"
      aria-label="Status: Extracted pending review"
    >
      <Sparkles className="w-3 h-3 text-amber-600" />
      <span>EXTRACTED (PENDING REVIEW)</span>
    </button>
  );
};
