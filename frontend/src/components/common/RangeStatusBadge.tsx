import React from 'react';
import { RangeStatus } from '../../types';
import { ArrowDownRight, ArrowUpRight, CheckCircle2, HelpCircle } from 'lucide-react';

interface RangeStatusBadgeProps {
  status: RangeStatus;
  className?: string;
}

export const RangeStatusBadge: React.FC<RangeStatusBadgeProps> = ({ status, className = '' }) => {
  switch (status) {
    case 'LOW':
      return (
        <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200/80 ${className}`}>
          <ArrowDownRight className="w-3 h-3 text-rose-600" />
          LOW
        </span>
      );
    case 'HIGH':
      return (
        <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200/80 ${className}`}>
          <ArrowUpRight className="w-3 h-3 text-amber-600" />
          HIGH
        </span>
      );
    case 'NORMAL':
      return (
        <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/80 ${className}`}>
          <CheckCircle2 className="w-3 h-3 text-emerald-600" />
          NORMAL
        </span>
      );
    case 'REFERENCE_RANGE_UNAVAILABLE':
    default:
      return (
        <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200 ${className}`} title="No reference range was specified in source report">
          <HelpCircle className="w-3 h-3 text-slate-400" />
          Range Unavailable
        </span>
      );
  }
};
