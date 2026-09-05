import React, { useState } from 'react';
import { Patient } from '../../types';
import { patientApi } from '../../services/api';
import { X, UserPlus, Save, AlertCircle } from 'lucide-react';

interface PatientIntakeModalProps {
  isOpen: boolean;
  onClose: () => void;
  onPatientCreatedOrUpdated: (p: Patient) => void;
  initialPatient?: Patient | null;
}

export const PatientIntakeModal: React.FC<PatientIntakeModalProps> = ({
  isOpen,
  onClose,
  onPatientCreatedOrUpdated,
  initialPatient,
}) => {
  const isEditing = Boolean(initialPatient);

  const [fullName, setFullName] = useState(initialPatient?.full_name || '');
  const [age, setAge] = useState(initialPatient?.age?.toString() || '');
  const [sex, setSex] = useState<'male' | 'female' | 'other'>(initialPatient?.sex || 'female');
  const [symptoms, setSymptoms] = useState(initialPatient?.symptoms || '');
  const [existingConditions, setExistingConditions] = useState(initialPatient?.existing_conditions || '');
  const [allergies, setAllergies] = useState(initialPatient?.allergies || '');
  const [currentMedications, setCurrentMedications] = useState(initialPatient?.current_medications || '');
  const [medicalHistory, setMedicalHistory] = useState(initialPatient?.medical_history || '');
  const [additionalNotes, setAdditionalNotes] = useState(initialPatient?.additional_notes || '');

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (!fullName.trim()) {
      setErrorMsg('Patient full name is required.');
      return;
    }

    const parsedAge = parseInt(age, 10);
    if (isNaN(parsedAge) || parsedAge < 0 || parsedAge > 125) {
      setErrorMsg('Please enter a valid age between 0 and 125.');
      return;
    }

    setIsSubmitting(true);
    try {
      if (isEditing && initialPatient) {
        const updated = await patientApi.updateIntake(initialPatient.id, {
          symptoms,
          existing_conditions: existingConditions,
          allergies,
          current_medications: currentMedications,
          medical_history: medicalHistory,
          additional_notes: additionalNotes,
        });
        onPatientCreatedOrUpdated(updated);
      } else {
        const created = await patientApi.create({
          full_name: fullName.trim(),
          age: parsedAge,
          sex,
          symptoms,
          existing_conditions: existingConditions,
          allergies,
          current_medications: currentMedications,
          medical_history: medicalHistory,
          additional_notes: additionalNotes,
        });
        onPatientCreatedOrUpdated(created);
      }
      onClose();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to save patient information.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
      <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-2xl w-full max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95">
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-sky-100 text-sky-700 flex items-center justify-center">
              <UserPlus className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">
                {isEditing ? `Edit Intake Record: ${initialPatient?.full_name}` : 'New Patient Intake'}
              </h3>
              <p className="text-xs text-slate-500">
                {isEditing ? 'Update clinical information provided manually by clinician or patient.' : 'Creates a persistent patient profile and assigns a unique Clinova Patient ID.'}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Error Banner */}
        {errorMsg && (
          <div className="mx-6 mt-4 p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 overflow-y-auto space-y-4 flex-1">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="sm:col-span-2">
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Full Name <span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                required
                disabled={isEditing}
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="e.g. Eleanor Vance"
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 disabled:bg-slate-100"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Age <span className="text-rose-500">*</span>
              </label>
              <input
                type="number"
                required
                disabled={isEditing}
                min={0}
                max={125}
                value={age}
                onChange={(e) => setAge(e.target.value)}
                placeholder="e.g. 58"
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 disabled:bg-slate-100"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Biological Sex <span className="text-rose-500">*</span>
              </label>
              <select
                disabled={isEditing}
                value={sex}
                onChange={(e) => setSex(e.target.value as any)}
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 disabled:bg-slate-100"
              >
                <option value="female">Female</option>
                <option value="male">Male</option>
                <option value="other">Other</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Documented Allergies
              </label>
              <input
                type="text"
                value={allergies}
                onChange={(e) => setAllergies(e.target.value)}
                placeholder="e.g. No known allergies (NKDA)"
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Active Medications & Dosages
            </label>
            <input
              type="text"
              value={currentMedications}
              onChange={(e) => setCurrentMedications(e.target.value)}
              placeholder="e.g. Metformin 500mg daily, Lisinopril 10mg daily"
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Existing Conditions / Diagnoses
            </label>
            <input
              type="text"
              value={existingConditions}
              onChange={(e) => setExistingConditions(e.target.value)}
              placeholder="e.g. Type 2 Diabetes, Hypertension"
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Reported Symptoms & Chief Complaints
            </label>
            <textarea
              rows={2}
              value={symptoms}
              onChange={(e) => setSymptoms(e.target.value)}
              placeholder="e.g. Mild shortness of breath, morning joint pain..."
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Medical History & Background
            </label>
            <textarea
              rows={2}
              value={medicalHistory}
              onChange={(e) => setMedicalHistory(e.target.value)}
              placeholder="e.g. Cholecystectomy in 2018, family history of coronary artery disease..."
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500"
            />
          </div>

          <div className="pt-2 flex items-center justify-end gap-3 border-t border-slate-200">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex items-center gap-1.5 px-5 py-2 text-xs font-semibold bg-sky-600 hover:bg-sky-700 text-white rounded-lg shadow-sm transition-colors cursor-pointer disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              {isSubmitting ? 'Saving...' : isEditing ? 'Update Intake' : 'Create Patient'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
