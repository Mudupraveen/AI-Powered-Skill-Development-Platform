import React, { useState } from 'react';
import { 
  HelpCircle, 
  Send, 
  Sparkles, 
  BookOpen, 
  AlertTriangle, 
  ArrowRight,
  Code2,
  Lightbulb
} from 'lucide-react';
import { api } from '../services/api';

export default function AskDoubt({ onPracticeTopic }) {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null); // { answer, suggested_topic }
  const [error, setError] = useState(null);

  const sampleQuestions = [
    "Explain the difference between SQL INNER JOIN and LEFT JOIN with examples.",
    "How does async and await work under the hood in Python?",
    "Why does FastAPI use Pydantic for request validation?",
    "When should I use CSS Flexbox vs CSS Grid?"
  ];

  const handleAsk = async (queryToAsk = question) => {
    if (!queryToAsk.trim()) return;

    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const data = await api.askDoubt(queryToAsk);
      setResponse(data);
    } catch (err) {
      setError(err.message || "Failed to get an answer from Claude. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-fadeIn">
      {/* Header */}
      <div className="border-b border-slate-800 pb-6">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-purple-500/10 text-purple-400 text-xs font-semibold mb-2 border border-purple-500/20">
          <Sparkles className="w-3.5 h-3.5" />
          AI Doubt Tutor Agent
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
          Ask a Doubt
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          Instant conceptual clarifications powered by Claude Sonnet 4.6 with tailored follow-up quiz practice.
        </p>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="font-semibold">Notice</p>
            <p className="mt-0.5 text-rose-200">{error}</p>
          </div>
        </div>
      )}

      {/* Input Box */}
      <div className="rounded-2xl bg-slate-900/80 border border-slate-800 p-5 sm:p-6 shadow-xl space-y-4">
        <label htmlFor="doubt-input" className="block text-xs font-semibold text-slate-300">
          What technical concept or question are you struggling with?
        </label>

        <div className="relative">
          <textarea
            id="doubt-input"
            rows={4}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. How does an INNER JOIN differ from a LEFT JOIN, and what happens when keys are NULL?"
            className="w-full rounded-xl bg-slate-950 border border-slate-800 p-4 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all resize-none"
          />
        </div>

        {/* Sample Chips */}
        <div className="space-y-2">
          <span className="text-xs text-slate-500 flex items-center gap-1">
            <Lightbulb className="w-3 h-3 text-amber-400" /> Quick suggestions:
          </span>
          <div className="flex flex-wrap gap-2">
            {sampleQuestions.map((sq, i) => (
              <button
                key={i}
                type="button"
                onClick={() => {
                  setQuestion(sq);
                  handleAsk(sq);
                }}
                className="text-xs text-left px-3 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-700/50 transition-colors"
              >
                {sq}
              </button>
            ))}
          </div>
        </div>

        {/* Submit Button */}
        <div className="flex items-center justify-end pt-2">
          <button
            id="btn-ask-doubt"
            onClick={() => handleAsk()}
            disabled={loading || !question.trim()}
            className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold text-sm shadow-md shadow-indigo-600/20 transition-all duration-150"
          >
            {loading ? (
              <>
                <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                Claude is analyzing...
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                Ask Claude
              </>
            )}
          </button>
        </div>
      </div>

      {/* Answer Display */}
      {response && (
        <div className="rounded-2xl bg-slate-900/90 border border-indigo-500/30 p-6 sm:p-8 space-y-6 shadow-2xl animate-fadeIn">
          <div className="flex items-center justify-between gap-4 border-b border-slate-800 pb-4">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-indigo-400" />
              <h3 className="font-bold text-base text-white">Claude's Explanation</h3>
            </div>
            {response.suggested_topic && (
              <span className="text-xs font-mono px-2.5 py-1 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-semibold">
                Topic Tag: {response.suggested_topic}
              </span>
            )}
          </div>

          {/* Formatted Text Content */}
          <div className="text-sm text-slate-200 leading-relaxed space-y-3 whitespace-pre-line font-sans">
            {response.answer}
          </div>

          {/* Practice Action Link if suggested_topic is present */}
          {response.suggested_topic && (
            <div className="p-4 rounded-xl bg-gradient-to-r from-indigo-950/60 to-purple-950/60 border border-indigo-500/40 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <p className="text-xs font-bold text-indigo-200 flex items-center gap-1.5">
                  <BookOpen className="w-4 h-4 text-indigo-400" />
                  Reinforce this understanding with an AI quiz
                </p>
                <p className="text-xs text-slate-400 mt-0.5">
                  Take a 4-question targeted diagnostic on <strong className="text-white">{response.suggested_topic}</strong> to test what you just learned.
                </p>
              </div>

              <button
                id="btn-practice-topic"
                onClick={() => onPracticeTopic(response.suggested_topic)}
                className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs shadow-md shadow-indigo-600/25 shrink-0 transition-transform duration-150 hover:scale-105"
              >
                Practice this topic ({response.suggested_topic})
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
