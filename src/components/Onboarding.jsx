import React, { useState, useEffect } from 'react';
import { User, CheckCircle2, AlertTriangle, ArrowRight, Sparkles, Layers } from 'lucide-react';
import { api } from '../services/api';

export default function Onboarding({ currentProfile, onProfileSaved }) {
  const [skills, setSkills] = useState({
    Python: 'Intermediate',
    SQL: 'Beginner',
    'HTML/CSS': 'Intermediate',
    FastAPI: 'Beginner'
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  // Sync with current profile if available
  useEffect(() => {
    if (currentProfile?.skills) {
      const initialSkills = {};
      Object.entries(currentProfile.skills).forEach(([topic, data]) => {
        initialSkills[topic] = data.rating || 'Beginner';
      });
      setSkills(prev => ({ ...prev, ...initialSkills }));
    }
  }, [currentProfile]);

  const ratingLevels = [
    { label: 'Beginner', value: 'Beginner', percent: '20%', desc: 'Basic syntax, concepts, and small scripts' },
    { label: 'Intermediate', value: 'Intermediate', percent: '50%', desc: 'Comfortable writing features & debugging' },
    { label: 'Advanced', value: 'Advanced', percent: '80%', desc: 'Architecture, optimization, & best practices' },
  ];

  const handleLevelChange = (topic, level) => {
    setSkills(prev => ({
      ...prev,
      [topic]: level
    }));
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      await api.updateProfile(skills);
      setSuccess(true);
      if (onProfileSaved) {
        onProfileSaved();
      }
    } catch (err) {
      setError(err.message || 'Failed to update skill profile.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8 animate-fadeIn">
      {/* Header */}
      <div className="border-b border-slate-800 pb-6">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-500/10 text-indigo-400 text-xs font-semibold mb-2 border border-indigo-500/20">
          <Layers className="w-3.5 h-3.5" />
          Skill Self-Calibration
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
          Self-Rate Your Technical Stack
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          Set your baseline proficiency to jumpstart your personalized learning roadmap.
          (Beginner = 20%, Intermediate = 50%, Advanced = 80%).
        </p>
      </div>

      {/* Error / Success feedback */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="font-semibold">Error saving profile</p>
            <p className="mt-0.5 text-rose-200">{error}</p>
          </div>
        </div>
      )}

      {success && (
        <div className="p-4 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 flex items-center gap-3">
          <CheckCircle2 className="w-5 h-5 shrink-0" />
          <p className="text-sm font-semibold">Profile updated successfully! Calibrated skills in database.</p>
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSave} className="space-y-6">
        {Object.keys(skills).map((topic) => (
          <div 
            key={topic}
            id={`skill-selector-${topic.toLowerCase().replace(/[^a-z0-9]/g, '-')}`}
            className="rounded-xl bg-slate-900/80 border border-slate-800 p-5 space-y-3"
          >
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-slate-100 text-base">{topic}</h3>
              <span className="text-xs text-indigo-400 font-mono font-medium">
                Active: {skills[topic]}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {ratingLevels.map((lvl) => {
                const isSelected = skills[topic] === lvl.value;
                return (
                  <button
                    key={lvl.value}
                    type="button"
                    onClick={() => handleLevelChange(topic, lvl.value)}
                    className={`flex flex-col text-left p-3.5 rounded-xl border transition-all duration-150 ${
                      isSelected
                        ? 'bg-indigo-600/20 border-indigo-500 shadow-md shadow-indigo-500/20'
                        : 'bg-slate-950/60 border-slate-800/80 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className={`text-sm font-semibold ${isSelected ? 'text-white' : 'text-slate-300'}`}>
                        {lvl.label}
                      </span>
                      <span className="text-xs font-mono font-bold text-slate-400">
                        {lvl.percent}
                      </span>
                    </div>
                    <span className="text-[11px] text-slate-400 mt-1 leading-snug">
                      {lvl.desc}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        ))}

        {/* Submit */}
        <div className="flex items-center justify-end pt-4">
          <button
            id="btn-save-profile"
            type="submit"
            disabled={loading}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold text-sm shadow-lg shadow-indigo-600/25 transition-all duration-150"
          >
            {loading ? (
              <>
                <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                Updating Profile...
              </>
            ) : (
              <>
                <CheckCircle2 className="w-4 h-4" />
                Save Profile & Calibrate Roadmap
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
