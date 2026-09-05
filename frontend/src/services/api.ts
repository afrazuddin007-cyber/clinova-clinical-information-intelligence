import axios from 'axios';
import {
  User, Patient, MedicalReport, ExtractedLabResult, ExtractedClinicalEntity,
  ReportComparisonResponse, Inconsistency, DoctorQueryResponse, PatientSummaryResponse,
  AuditLogEntry
} from '../types';

const API_BASE_URL = '/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for JWT
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('clinova_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('clinova_token');
      localStorage.removeItem('clinova_user');
      // If not on login, redirect
      if (!window.location.pathname.includes('login')) {
        window.location.reload();
      }
    }
    return Promise.reject(error);
  }
);

// Auth endpoints
export const authApi = {
  login: async (email: string, password: string) => {
    const res = await apiClient.post<{ access_token: string; user: User }>('/auth/login', { email, password });
    return res.data;
  },
  register: async (email: string, password: string, full_name: string) => {
    const res = await apiClient.post<{ access_token: string; user: User }>('/auth/register', { email, password, full_name });
    return res.data;
  },
  registerOrg: async (organization_name: string, admin_name: string, email: string, password: string) => {
    const res = await apiClient.post<{ access_token: string; user: User }>('/auth/register-org', {
      organization_name,
      admin_name,
      email,
      password,
    });
    return res.data;
  },
  getMe: async () => {
    const res = await apiClient.get<User>('/auth/me');
    return res.data;
  },
};

// Patient endpoints
export const patientApi = {
  list: async () => {
    const res = await apiClient.get<Patient[]>('/patients');
    return res.data;
  },
  get: async (patientId: string) => {
    const res = await apiClient.get<Patient>(`/patients/${patientId}`);
    return res.data;
  },
  create: async (data: Partial<Patient>) => {
    const res = await apiClient.post<Patient>('/patients', data);
    return res.data;
  },
  updateIntake: async (patientId: string, data: Partial<Patient>) => {
    const res = await apiClient.put<Patient>(`/patients/${patientId}/intake`, data);
    return res.data;
  },
  getSummary: async (patientId: string) => {
    const res = await apiClient.get<PatientSummaryResponse>(`/patients/${patientId}/summary`);
    return res.data;
  },
};

// Report endpoints
export const reportApi = {
  list: async (patientId: string) => {
    const res = await apiClient.get<MedicalReport[]>(`/patients/${patientId}/reports`);
    return res.data;
  },
  listAll: async () => {
    const res = await apiClient.get<MedicalReport[]>('/reports');
    return res.data;
  },
  upload: async (patientId: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await apiClient.post<MedicalReport>(`/patients/${patientId}/reports`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },
  getFileUrl: (reportId: string) => `/api/v1/reports/${reportId}/file`,
};

// Lab & Entities endpoints
export const clinicalApi = {
  getLabs: async (patientId: string) => {
    const res = await apiClient.get<ExtractedLabResult[]>(`/patients/${patientId}/labs`);
    return res.data;
  },
  getEntities: async (patientId: string) => {
    const res = await apiClient.get<ExtractedClinicalEntity[]>(`/patients/${patientId}/entities`);
    return res.data;
  },
};

// Verification endpoints
export const verificationApi = {
  getPending: async () => {
    const res = await apiClient.get<ExtractedLabResult[]>('/results/pending');
    return res.data;
  },
  verify: async (resultId: string) => {
    const res = await apiClient.post<ExtractedLabResult>(`/results/${resultId}/verify`, {});
    return res.data;
  },
  edit: async (resultId: string, data: { new_value: string; new_unit?: string; new_reference_range?: string; edit_reason: string }) => {
    const res = await apiClient.put<ExtractedLabResult>(`/results/${resultId}/edit`, data);
    return res.data;
  },
  reject: async (resultId: string, rejection_reason: string) => {
    const res = await apiClient.post<ExtractedLabResult>(`/results/${resultId}/reject`, { rejection_reason });
    return res.data;
  },
};

// Comparison endpoint
export const comparisonApi = {
  compare: async (patientId: string, reportAId: string, reportBId: string) => {
    const res = await apiClient.get<ReportComparisonResponse>(
      `/patients/${patientId}/compare?report_a=${reportAId}&report_b=${reportBId}`
    );
    return res.data;
  },
};

// Conflict endpoints
export const conflictApi = {
  getConflicts: async (patientId: string) => {
    const res = await apiClient.get<Inconsistency[]>(`/patients/${patientId}/conflicts`);
    return res.data;
  },
  acknowledge: async (conflictId: string) => {
    const res = await apiClient.post<Inconsistency>(`/conflicts/${conflictId}/acknowledge`, {});
    return res.data;
  },
};

// Doctor Intelligence Q&A endpoint
export const intelligenceApi = {
  ask: async (patientId: string, query: string) => {
    const res = await apiClient.post<DoctorQueryResponse>(`/patients/${patientId}/ask`, { query });
    return res.data;
  },
};

// Demo endpoint
export const demoApi = {
  seed: async () => {
    const res = await apiClient.post<{ message: string; patient_id: string; id: string }>('/demo/seed', {});
    return res.data;
  },
};

// Audit & Activity endpoints
export const auditApi = {
  getLogs: async () => {
    const res = await apiClient.get<AuditLogEntry[]>('/audit/logs');
    return res.data;
  },
};
