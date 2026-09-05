import React, { useState, useEffect, useRef } from 'react';
import { DoctorQueryResponse } from '../../types';
import { intelligenceApi } from '../../services/api';
import {
  Bot,
  Send,
  Sparkles,
  FileText,
  ShieldAlert,
  Loader2,
  AlertTriangle,
  Layers,
  User,
  Pill,
  GitCompare,
  RotateCcw,
  ShieldCheck,
  ExternalLink
} from 'lucide-react';

interface DoctorIntelligencePanelProps {
  patientId: string;
}

interface QuickAction {
  id: string;
  title: string;
  subtitle: string;
  prompt: string;
  icon: React.ReactNode;
}

export const DoctorIntelligencePanel: React.FC<DoctorIntelligencePanelProps> = ({ patientId }) => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversation, setConversation] = useState<Array<{ role: 'user' | 'assistant'; content: string; citations?: any[] }>>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const currentPatientIdRef = useRef<string>(patientId);

  // Patient isolation: reset conversation state whenever patientId changes
  useEffect(() => {
    currentPatientIdRef.current = patientId;
    setConversation([]);
    setQuery('');
    setLoading(false);
  }, [patientId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversation, loading]);

  const quickActions: QuickAction[] = [
    {
      id: 'lab-all',
      title: 'All laboratory findings',
      subtitle: 'Complete panel with values, units & ranges',
      prompt: 'List all laboratory findings for this patient',
      icon: <Layers className="w-4 h-4 text-sky-600" />,
    },
    {
      id: 'lab-abnormal',
      title: 'Abnormal laboratory findings',
      subtitle: 'Deterministically evaluated out-of-range labs',
      prompt: 'What are the abnormal findings in the latest medical report? Give the test name, value, reference range, and source page for each.',
      icon: <AlertTriangle className="w-4 h-4 text-amber-600" />,
    },
    {
      id: 'patient-info',
      title: 'Patient information',
      subtitle: 'Blood type, allergies, conditions & symptoms',
      prompt: "What is the patient's blood type, allergies, symptoms, conditions, and medications?",
      icon: <User className="w-4 h-4 text-emerald-600" />,
    },
    {
      id: 'medications',
      title: 'Current medications',
      subtitle: 'Intake and report medications with provenance',
      prompt: 'What medications are documented for this patient? Include dosages and source documents.',
      icon: <Pill className="w-4 h-4 text-indigo-600" />,
    },
    {
      id: 'conflicts',
      title: 'Conflicts & discrepancies',
      subtitle: 'Cross-record contradictions in intake vs reports',
      prompt: "What conflicts or discrepancies exist between the patient's records?",
      icon: <ShieldAlert className="w-4 h-4 text-rose-600" />,
    },
    {
      id: 'provenance',
      title: 'Source & provenance',
      subtitle: 'Exact document, page location & quote verification',
      prompt: "What is the source document and page for the patient's latest lab results?",
      icon: <FileText className="w-4 h-4 text-blue-600" />,
    },
    {
      id: 'compare',
      title: 'Compare reports',
      subtitle: 'Longitudinal parameter differences between reports',
      prompt: 'What changed between the last two reports?',
      icon: <GitCompare className="w-4 h-4 text-teal-600" />,
    },
    {
      id: 'summary',
      title: 'Patient summary',
      subtitle: 'Deterministic overview of documented records',
      prompt: "Provide a clinical summary of this patient's records.",
      icon: <Sparkles className="w-4 h-4 text-purple-600" />,
    },
  ];

  const handleSendQuery = async (queryText: string) => {
    if (!queryText.trim() || loading) return;

    const userMsg = queryText.trim();
    const queryPatientId = patientId;
    setQuery('');
    setConversation((prev) => [...prev, { role: 'user', content: userMsg }]);
    setLoading(true);

    try {
      const response: DoctorQueryResponse = await intelligenceApi.ask(patientId, userMsg);
      // Discard response if patient was switched while query was in-flight
      if (currentPatientIdRef.current !== queryPatientId) return;

      setConversation((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: response.answer,
          citations: response.citations,
        },
      ]);
    } catch (err: any) {
      if (currentPatientIdRef.current !== queryPatientId) return;

      setConversation((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: "An error occurred retrieving structured records for this query. Please verify network connectivity.",
          citations: [],
        },
      ]);
    } finally {
      if (currentPatientIdRef.current === queryPatientId) {
        setLoading(false);
      }
    }
  };

  const handleResetConversation = () => {
    setConversation([]);
    setQuery('');
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-xs flex flex-col h-[600px] overflow-hidden">
      {/* Panel Header */}
      <div className="p-3.5 sm:p-4 border-b border-slate-200 bg-slate-50/80 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-slate-900 text-white flex items-center justify-center shadow-xs">
            <Bot className="w-4 h-4 text-sky-400" />
          </div>
          <div>
            <h3 className="text-xs sm:text-sm font-bold text-slate-900 flex items-center gap-2">
              Doctor Intelligence
              <span className="text-[10px] font-semibold text-sky-700 bg-sky-100/90 border border-sky-200 px-1.5 py-0.2 rounded-full">
                Grounded Retrieval
              </span>
            </h3>
            <p className="text-[11px] text-slate-500">
              Deterministic, evidence-grounded queries against verified structured records
            </p>
          </div>
        </div>

        {conversation.length > 0 && (
          <button
            type="button"
            onClick={handleResetConversation}
            className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-100 border border-slate-200 rounded-lg shadow-2xs transition-colors cursor-pointer"
            title="Reset conversation and return to quick actions"
          >
            <RotateCcw className="w-3.5 h-3.5 text-slate-500" />
            <span className="hidden sm:inline">Reset</span>
          </button>
        )}
      </div>

      {/* Main Conversation & Empty State Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
        {conversation.length === 0 ? (
          /* Polished Empty State Panel */
          <div className="h-full flex flex-col justify-center max-w-2xl mx-auto py-2">
            <div className="text-center mb-5">
              <div className="inline-flex p-2.5 rounded-2xl bg-sky-50 border border-sky-100 text-sky-600 mb-3 shadow-2xs">
                <ShieldCheck className="w-6 h-6" />
              </div>
              <h4 className="text-base sm:text-lg font-bold text-slate-900 tracking-tight">
                Ask about this patient's verified records
              </h4>
              <p className="text-xs text-slate-500 mt-1 max-w-lg mx-auto">
                Retrieve documented labs, medications, patient information, conflicts, comparisons, and source evidence.
              </p>

              {/* Prominent Non-Diagnostic Advisory */}
              <div className="mt-3 inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-100 border border-slate-200 text-[11px] text-slate-600 font-medium">
                <ShieldAlert className="w-3.5 h-3.5 text-slate-500" />
                <span>Non-Diagnostic: Clinova retrieves records; it does not diagnose or prescribe.</span>
              </div>
            </div>

            {/* 8 Quick Action Cards Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {quickActions.map((action) => (
                <button
                  key={action.id}
                  type="button"
                  onClick={() => handleSendQuery(action.prompt)}
                  disabled={loading}
                  className="p-3 rounded-xl border border-slate-200/90 bg-slate-50/50 hover:bg-white hover:border-sky-300 hover:shadow-sm text-left transition-all cursor-pointer group flex items-start gap-3 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
                >
                  <div className="p-2 rounded-lg bg-white border border-slate-200/80 shadow-2xs group-hover:scale-105 transition-transform mt-0.5">
                    {action.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-slate-900 group-hover:text-sky-700 transition-colors text-xs flex items-center justify-between">
                      <span className="truncate">{action.title}</span>
                    </div>
                    <div className="text-[11px] text-slate-500 leading-snug line-clamp-1 mt-0.5">
                      {action.subtitle}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* Active Chat Thread */
          conversation.map((msg, idx) => (
            <div
              key={idx}
              className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
            >
              <div
                className={`max-w-[90%] sm:max-w-[85%] rounded-2xl p-3.5 leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-slate-900 text-white shadow-xs'
                    : 'bg-slate-50/90 border border-slate-200/80 text-slate-800 shadow-2xs'
                }`}
              >
                <div className="whitespace-pre-wrap text-xs sm:text-[13px]">{msg.content}</div>

                {/* Grounded Source Citations */}
                {msg.citations && msg.citations.length > 0 && (
                  <div className="mt-3 pt-2.5 border-t border-slate-200/80 space-y-1.5">
                    <span className="text-[10px] font-bold text-slate-500 block uppercase tracking-wider">
                      Traceable Source Citations ({msg.citations.length}):
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {msg.citations.map((c, cIdx) => (
                        <span
                          key={cIdx}
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-medium bg-white text-slate-700 border border-slate-200 shadow-2xs"
                          title={c.snippet || undefined}
                        >
                          <FileText className="w-3 h-3 text-sky-600" />
                          <span>{c.source_title}</span>
                          {c.page_number && <span className="text-slate-400 font-mono">(p. {c.page_number})</span>}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))
        )}

        {/* Loading Spinner */}
        {loading && (
          <div className="flex items-center gap-2 text-xs text-sky-700 bg-sky-50/80 p-3 rounded-xl border border-sky-100 max-w-sm">
            <Loader2 className="w-4 h-4 animate-spin text-sky-600" />
            <span className="font-medium">Retrieving grounded facts from patient records...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick Prompts Bar for Active Conversation (Wrapped & Non-overflowing) */}
      {conversation.length > 0 && (
        <div className="px-3 py-2 border-t border-slate-100 bg-slate-50/60 flex flex-wrap items-center gap-1.5 text-[11px]">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mr-1">
            Quick Actions:
          </span>
          {quickActions.map((action) => (
            <button
              key={action.id}
              type="button"
              disabled={loading}
              onClick={() => handleSendQuery(action.prompt)}
              className="px-2 py-1 rounded-md bg-white border border-slate-200 hover:border-sky-300 hover:text-sky-700 text-slate-700 font-medium whitespace-nowrap transition-colors cursor-pointer shadow-2xs disabled:opacity-50 text-[11px]"
            >
              {action.title}
            </button>
          ))}
        </div>
      )}

      {/* Input Box */}
      <div className="p-3 sm:p-3.5 border-t border-slate-200 bg-white">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendQuery(query);
          }}
          className="flex items-center gap-2"
        >
          <input
            type="text"
            value={query}
            disabled={loading}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask about documented labs, medications, conflicts, or trends..."
            className="flex-1 px-3.5 py-2 text-xs sm:text-[13px] border border-slate-200 rounded-xl bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 disabled:opacity-50 transition-all placeholder:text-slate-400"
            aria-label="Clinical inquiry prompt"
          />
          <button
            type="submit"
            disabled={!query.trim() || loading}
            aria-label="Send clinical inquiry"
            className="px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold disabled:opacity-40 transition-colors cursor-pointer shadow-xs flex items-center gap-1.5"
          >
            <span>Ask</span>
            <Send className="w-3 h-3 text-sky-400" />
          </button>
        </form>

        <div className="mt-2 text-[10px] text-slate-400 text-center flex items-center justify-center gap-1">
          <ShieldAlert className="w-3 h-3 text-slate-400" />
          <span>Clinova information synthesis only. Not intended for diagnosis or prescribing.</span>
        </div>
      </div>
    </div>
  );
};
