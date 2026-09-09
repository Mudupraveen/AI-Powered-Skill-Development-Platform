import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import Dashboard from './components/Dashboard';
import QuizPage from './components/QuizPage';
import AskDoubt from './components/AskDoubt';
import Onboarding from './components/Onboarding';
import { api } from './services/api';
import { AlertCircle, RefreshCw } from 'lucide-react';

export default function App() {
  const [currentTab, setCurrentTab] = useState('dashboard');
  const [activeQuizTopic, setActiveQuizTopic] = useState('SQL');
  
  const [profile, setProfile] = useState(null);
  const [roadmap, setRoadmap] = useState(null);
  const [loading, setLoading] = useState(true);
  const [globalError, setGlobalError] = useState(null);

  const fetchAppData = async () => {
    setLoading(true);
    setGlobalError(null);
    try {
      const [profileData, roadmapData] = await Promise.all([
        api.getProfile(),
        api.getRoadmap(),
      ]);
      setProfile(profileData);
      setRoadmap(roadmapData);
    } catch (err) {
      console.error("Error loading app data:", err);
      setGlobalError(err.message || "Failed to communicate with backend server.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAppData();
  }, []);

  const handleReplanRoadmap = async () => {
    const updatedPlan = await api.replanRoadmap();
    setRoadmap(updatedPlan);
    // Also refresh profile so reinforcement flags match
    const refreshedProfile = await api.getProfile();
    setProfile(refreshedProfile);
    return updatedPlan;
  };

  const handleStartQuiz = (topic) => {
    setActiveQuizTopic(topic);
    setCurrentTab('quiz');
  };

  const handlePracticeTopic = (topic) => {
    // Sanitize topic name if needed (e.g. if Claude gives "SQL JOINs", map to "SQL" or keep as is)
    let matchedTopic = topic;
    const cleanLower = topic.toLowerCase();
    if (cleanLower.includes('sql') || cleanLower.includes('join')) matchedTopic = 'SQL';
    else if (cleanLower.includes('python')) matchedTopic = 'Python';
    else if (cleanLower.includes('fastapi')) matchedTopic = 'FastAPI';
    else if (cleanLower.includes('html') || cleanLower.includes('css')) matchedTopic = 'HTML/CSS';

    setActiveQuizTopic(matchedTopic);
    setCurrentTab('quiz');
  };

  const handleProfileSaved = async () => {
    await fetchAppData();
    // After profile saved, navigate to dashboard to see updated scores
    setCurrentTab('dashboard');
  };

  const handleQuizComplete = async () => {
    // Refresh scores and roadmap in background
    try {
      const [profileData, roadmapData] = await Promise.all([
        api.getProfile(),
        api.getRoadmap(),
      ]);
      setProfile(profileData);
      setRoadmap(roadmapData);
    } catch (e) {
      console.warn("Could not background-refresh data:", e);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col text-slate-100">
      {/* Top Navbar */}
      <Navbar 
        currentTab={currentTab} 
        setCurrentTab={setCurrentTab}
        studentName={profile?.name || "Demo Student"}
      />

      {/* Global Server Connection Error Banner */}
      {globalError && (
        <div className="bg-rose-950/80 border-b border-rose-500/30 px-4 py-3 text-rose-200">
          <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
            <div className="flex items-center gap-2 text-xs sm:text-sm">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{globalError}</span>
            </div>
            <button
              onClick={fetchAppData}
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 text-xs font-semibold border border-rose-500/30 transition-colors"
            >
              <RefreshCw className="w-3 h-3" /> Retry
            </button>
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {currentTab === 'dashboard' && (
          <Dashboard
            profile={profile}
            roadmap={roadmap}
            loading={loading}
            error={globalError}
            onReplanRoadmap={handleReplanRoadmap}
            onStartQuiz={handleStartQuiz}
            onGoToOnboarding={() => setCurrentTab('profile')}
          />
        )}

        {currentTab === 'quiz' && (
          <QuizPage
            initialTopic={activeQuizTopic}
            onQuizComplete={handleQuizComplete}
            onGoToDashboard={() => setCurrentTab('dashboard')}
          />
        )}

        {currentTab === 'doubt' && (
          <AskDoubt
            onPracticeTopic={handlePracticeTopic}
          />
        )}

        {currentTab === 'profile' && (
          <Onboarding
            currentProfile={profile}
            onProfileSaved={handleProfileSaved}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 py-6 text-center text-xs text-slate-500 bg-slate-950">
        <p>AI-Powered Learning & Skill Development Platform • Anthropic Claude Sonnet 4.6 • FastAPI + React</p>
      </footer>
    </div>
  );
}
