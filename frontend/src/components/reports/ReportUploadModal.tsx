import React, { useState, useRef } from 'react';
import { reportApi } from '../../services/api';
import { MedicalReport } from '../../types';
import { UploadCloud, X, FileCheck2, AlertCircle, Loader2, ArrowRight } from 'lucide-react';

interface ReportUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  patientId: string;
  onUploadSuccess: (report: MedicalReport) => void;
}

type PipelineStep = 'IDLE' | 'UPLOADING' | 'PROCESSING' | 'EXTRACTING' | 'VALIDATING' | 'REVIEW' | 'COMPLETED';

export const ReportUploadModal: React.FC<ReportUploadModalProps> = ({
  isOpen,
  onClose,
  patientId,
  onUploadSuccess,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState<boolean>(false);
  const [step, setStep] = useState<PipelineStep>('IDLE');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const validateAndSetFile = (file: File) => {
    setErrorMessage(null);
    const validExtensions = ['.pdf', '.png', '.jpg', '.jpeg'];
    const hasValidExt = validExtensions.some((ext) => file.name.toLowerCase().endsWith(ext));

    if (!hasValidExt) {
      setErrorMessage('Unsupported file format. Please upload a PDF, PNG, or JPEG medical report.');
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setErrorMessage('File size exceeds the 10 MB limit.');
      return;
    }

    setSelectedFile(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const handleStartUploadAndPipeline = async () => {
    if (!selectedFile) return;

    setStep('UPLOADING');
    setErrorMessage(null);

    try {
      // Step 1: Uploading
      await new Promise((r) => setTimeout(r, 400));
      setStep('PROCESSING');

      // Step 2: Processing & Extracting
      await new Promise((r) => setTimeout(r, 400));
      setStep('EXTRACTING');

      const report = await reportApi.upload(patientId, selectedFile);

      // Step 3: Validating ranges deterministically
      setStep('VALIDATING');
      await new Promise((r) => setTimeout(r, 400));

      // Step 4: Ready for Review
      setStep('REVIEW');
      await new Promise((r) => setTimeout(r, 300));

      setStep('COMPLETED');
      onUploadSuccess(report);
      setTimeout(() => {
        onClose();
        setStep('IDLE');
        setSelectedFile(null);
      }, 700);
    } catch (err: any) {
      setStep('IDLE');
      const detail = err.response?.data?.detail || 'Document processing failed. Please check the file format and try again.';
      setErrorMessage(detail);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
      <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-xl w-full overflow-hidden animate-in fade-in zoom-in-95">
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-sky-100 text-sky-700 flex items-center justify-center">
              <UploadCloud className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">Upload Medical Report</h3>
              <p className="text-xs text-slate-500">PDF, PNG, or JPEG format (max 10MB)</p>
            </div>
          </div>
          {step === 'IDLE' && (
            <button
              type="button"
              onClick={onClose}
              className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Pipeline Stepper Visualizer */}
        <div className="bg-slate-900 text-white px-5 py-3 text-xs">
          <div className="flex items-center justify-between text-[11px] font-mono tracking-wider">
            <span className={step === 'UPLOADING' ? 'text-sky-400 font-bold' : step === 'IDLE' ? 'text-slate-400' : 'text-emerald-400'}>
              1. UPLOAD
            </span>
            <ArrowRight className="w-3 h-3 text-slate-600" />
            <span className={step === 'PROCESSING' ? 'text-sky-400 font-bold' : ['EXTRACTING', 'VALIDATING', 'REVIEW', 'COMPLETED'].includes(step) ? 'text-emerald-400' : 'text-slate-500'}>
              2. PROCESSING
            </span>
            <ArrowRight className="w-3 h-3 text-slate-600" />
            <span className={step === 'EXTRACTING' ? 'text-sky-400 font-bold' : ['VALIDATING', 'REVIEW', 'COMPLETED'].includes(step) ? 'text-emerald-400' : 'text-slate-500'}>
              3. EXTRACTING
            </span>
            <ArrowRight className="w-3 h-3 text-slate-600" />
            <span className={step === 'VALIDATING' ? 'text-sky-400 font-bold' : ['REVIEW', 'COMPLETED'].includes(step) ? 'text-emerald-400' : 'text-slate-500'}>
              4. VALIDATING
            </span>
            <ArrowRight className="w-3 h-3 text-slate-600" />
            <span className={['REVIEW', 'COMPLETED'].includes(step) ? 'text-emerald-400 font-bold' : 'text-slate-500'}>
              5. REVIEW
            </span>
          </div>
        </div>

        {/* Content Body */}
        <div className="p-6">
          {errorMessage && (
            <div className="mb-4 p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
              <span>{errorMessage}</span>
            </div>
          )}

          {step === 'IDLE' ? (
            <div>
              <div
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
                  dragActive ? 'border-sky-500 bg-sky-50/50' : 'border-slate-300 hover:border-slate-400 bg-slate-50/50'
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.png,.jpg,.jpeg"
                  className="hidden"
                  onChange={handleFileInput}
                />
                <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-sky-50 text-sky-600 flex items-center justify-center">
                  <UploadCloud className="w-6 h-6" />
                </div>
                <div className="text-sm font-semibold text-slate-800 mb-1">
                  Drag and drop report here, or <span className="text-sky-600 underline">browse files</span>
                </div>
                <p className="text-xs text-slate-500">Supported: PDF (Complete blood counts, metabolic panels, discharge summaries), PNG, JPG</p>
              </div>

              {selectedFile && (
                <div className="mt-4 p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between">
                  <div className="flex items-center gap-2.5 truncate">
                    <FileCheck2 className="w-4 h-4 text-emerald-600 shrink-0" />
                    <span className="text-xs font-medium text-slate-800 truncate">{selectedFile.name}</span>
                    <span className="text-[11px] text-slate-400 shrink-0">
                      ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setSelectedFile(null)}
                    className="text-xs text-rose-600 hover:text-rose-800 font-medium ml-2"
                  >
                    Remove
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="py-10 text-center space-y-3">
              <Loader2 className="w-8 h-8 text-sky-600 animate-spin mx-auto" />
              <div className="text-sm font-bold text-slate-800 capitalize">
                {step.toLowerCase()} Report...
              </div>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                {step === 'UPLOADING' && 'Transferring encrypted document securely to clinical storage...'}
                {step === 'PROCESSING' && 'Parsing document layout, pages, and metadata...'}
                {step === 'EXTRACTING' && 'Running Gemini 2.5 Flash strict schema extraction...'}
                {step === 'VALIDATING' && 'Executing deterministic reference-range math & conflict scans...'}
                {step === 'REVIEW' && 'Record updated and ready for clinician verification!'}
                {step === 'COMPLETED' && 'Extraction complete! Refreshing workspace...'}
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        {step === 'IDLE' && (
          <div className="p-4 bg-slate-50 border-t border-slate-200 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 hover:bg-slate-200/50 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={!selectedFile}
              onClick={handleStartUploadAndPipeline}
              className="flex items-center gap-1.5 px-5 py-2 text-xs font-semibold bg-sky-600 hover:bg-sky-700 text-white rounded-lg shadow-sm transition-colors cursor-pointer disabled:opacity-50"
            >
              <UploadCloud className="w-4 h-4" />
              Process Report
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
