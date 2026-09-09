const API_BASE_URL = "http://localhost:8000";

async function request(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const defaultHeaders = {
    "Content-Type": "application/json",
  };

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...defaultHeaders,
        ...options.headers,
      },
    });

    if (!response.ok) {
      let errorMsg = `Server error (${response.status})`;
      try {
        const errorData = await response.json();
        if (errorData.detail) {
          errorMsg = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
        }
      } catch (e) {
        // Response wasn't JSON
      }
      throw new Error(errorMsg);
    }

    return await response.json();
  } catch (error) {
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      throw new Error("Cannot connect to backend server. Make sure FastAPI is running on http://localhost:8000.");
    }
    throw error;
  }
}

export const api = {
  // Profile
  getProfile: () => request('/api/profile'),
  updateProfile: (skills) => request('/api/profile', {
    method: 'POST',
    body: JSON.stringify({ skills }),
  }),

  // Assessment
  startAssessment: (topic) => request(`/api/assess/${encodeURIComponent(topic)}`, {
    method: 'POST',
  }),
  submitAssessment: (topic, quizId, answers) => request(`/api/assess/${encodeURIComponent(topic)}/submit`, {
    method: 'POST',
    body: JSON.stringify({
      quiz_id: quizId,
      answers: answers,
    }),
  }),

  // Roadmap
  getRoadmap: () => request('/api/roadmap'),
  replanRoadmap: () => request('/api/roadmap/replan', {
    method: 'POST',
  }),

  // Ask Doubt
  askDoubt: (question) => request('/api/ask', {
    method: 'POST',
    body: JSON.stringify({ question }),
  }),
};
