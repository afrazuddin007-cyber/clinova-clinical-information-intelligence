import React, { useState } from 'react';
import { ExtractedLabResult } from '../../types';
import { RangeStatusBadge } from '../common/RangeStatusBadge';
import { ProvenanceBadge } from '../common/ProvenanceBadge';
import { Search, Filter, HelpCircle, FileText, ExternalLink, ShieldCheck } from 'lucide-react';

interface StructuredLabsTableProps {
  labs: ExtractedLabResult[];
  onInspectProvenance: (lab: ExtractedLabResult) => void;
  onVerifyClick?: (lab: ExtractedLabResult) => void;
}

export const StructuredLabsTable: React.FC<StructuredLabsTableProps> = ({
  labs,
  onInspectProvenance,
  onVerifyClick,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'ABNORMAL' | 'PENDING'>('ALL');

  // STRICT REQUIREMENT: Keep ALL findings visible. Never slice, truncate, or paginate.
  const filteredLabs = labs.filter((lab) => {
    const matchesSearch = lab.test_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (lab.raw_reference_range || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (lab.unit || '').toLowerCase().includes(searchTerm.toLowerCase());

    if (!matchesSearch) return false;

    if (statusFilter === 'ABNORMAL') {
      return lab.range_status === 'LOW' || lab.range_status === 'HIGH';
    }
    if (statusFilter === 'PENDING') {
      return lab.verification_status === 'PENDING_VERIFICATION';
    }
    return true;
  });

  const abnormalCount = labs.filter((l) => l.range_status === 'LOW' || l.range_status === 'HIGH').length;
  const pendingCount = labs.filter((l) => l.verification_status === 'PENDING_VERIFICATION').length;

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
      {/* Table Header & Search Controls */}
      <div className="p-4 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50/70">
        <div>
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            Structured Laboratory Results
            <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-slate-200 text-slate-700">
              {labs.length} findings
            </span>
          </h3>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Reference-range aware evaluations derived strictly from source documentation
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Search Input */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search all findings..."
              className="pl-8 pr-3 py-1.5 text-xs border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 w-48 text-slate-800 placeholder:text-slate-400"
              aria-label="Filter laboratory tests"
            />
          </div>

          {/* Status Filter Dropdown */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as any)}
            className="px-2.5 py-1.5 text-xs border border-slate-200 rounded-lg bg-white text-slate-700 font-medium focus:outline-none focus:ring-2 focus:ring-sky-500/20 cursor-pointer"
            aria-label="Filter tests by clinical range status"
          >
            <option value="ALL">All Findings ({labs.length})</option>
            <option value="ABNORMAL">Out of Range ({abnormalCount})</option>
            <option value="PENDING">Pending Review ({pendingCount})</option>
          </select>
        </div>
      </div>

      {/* Table Body with Sticky Header & Full Height */}
      {filteredLabs.length === 0 ? (
        <div className="py-16 text-center text-slate-400 text-xs">
          No matching laboratory findings in verified records.
        </div>
      ) : (
        <div className="overflow-x-auto max-h-[640px] overflow-y-auto">
          <table className="w-full text-left text-xs border-collapse">
            {/* Subtle Sticky Header */}
            <thead className="sticky top-0 z-10 bg-slate-50/95 backdrop-blur-xs border-b border-slate-200 shadow-2xs text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
              <tr>
                <th className="py-3 px-4">Test / Biomarker</th>
                <th className="py-3 px-4">Measured Result</th>
                <th className="py-3 px-4">Unit</th>
                <th className="py-3 px-4">Source Reference Range</th>
                <th className="py-3 px-4">Clinova Status</th>
                <th className="py-3 px-4">Verification</th>
                <th className="py-3 px-4 text-right">Evidence</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {filteredLabs.map((lab) => (
                <tr
                  key={lab.id}
                  className="hover:bg-sky-50/30 focus-within:bg-sky-50/40 transition-colors group"
                >
                  {/* Test Name */}
                  <td className="py-3 px-4 font-semibold text-slate-900">
                    <div>{lab.test_name}</div>
                    {lab.human_override_notes && (
                      <span className="block text-[10px] text-emerald-600 font-normal italic mt-0.5">
                        Edited: {lab.human_override_notes}
                      </span>
                    )}
                  </td>

                  {/* Measured Result */}
                  <td className="py-3 px-4 font-mono font-bold text-slate-900 text-sm">
                    {lab.raw_value}
                  </td>

                  {/* Unit */}
                  <td className="py-3 px-4 font-mono text-slate-600 text-[11px]">
                    {lab.unit || '—'}
                  </td>

                  {/* Reference Range */}
                  <td className="py-3 px-4 font-mono text-slate-700 text-[11px]">
                    {lab.raw_reference_range ? (
                      lab.raw_reference_range
                    ) : (
                      <span className="text-slate-400 italic">None printed on report</span>
                    )}
                  </td>

                  {/* Clinova Status */}
                  <td className="py-3 px-4">
                    <RangeStatusBadge status={lab.range_status} />
                  </td>

                  {/* Verification Status */}
                  <td className="py-3 px-4">
                    <ProvenanceBadge
                      provenance={lab.provenance_type}
                      verificationStatus={lab.verification_status}
                      onClick={() => onInspectProvenance(lab)}
                    />
                  </td>

                  {/* Evidence / Trace Source Action */}
                  <td className="py-3 px-4 text-right">
                    <button
                      type="button"
                      onClick={() => onInspectProvenance(lab)}
                      className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-semibold text-sky-700 bg-sky-50 hover:bg-sky-100 border border-sky-200 rounded-lg shadow-2xs transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-sky-500/30"
                      title="Trace source document, page location, and verbatim evidence quote"
                      aria-label={`Trace source evidence for ${lab.test_name}`}
                    >
                      <FileText className="w-3.5 h-3.5 text-sky-600" />
                      <span>Trace Source</span>
                      <span className="text-[10px] font-mono text-sky-600 bg-white px-1 py-0.2 rounded border border-sky-200 ml-0.5">
                        p. {lab.page_number}
                      </span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
