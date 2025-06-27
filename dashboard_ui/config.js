/**
 * Dashboard UI Configuration
 * --------------------------
 * Central configuration file for the AI Engine dashboard.
 * Contains API endpoints, feature flags, and environment-specific settings.
 */

// Determine environment
const isDevelopment = process.env.NODE_ENV !== 'production';

// Base API URLs
export const API_URLS = {
  // Main backend API
  BACKEND_BASE: isDevelopment 
    ? 'http://localhost:8000'
    : process.env.NEXT_PUBLIC_API_URL || 'https://api.autoops.example.com',
  
  // Agent control API
  AGENT_CONTROL_BASE: isDevelopment
    ? 'http://localhost:8001'
    : process.env.NEXT_PUBLIC_AGENT_API_URL || 'https://agent.autoops.example.com',
};

// API Endpoints
export const ENDPOINTS = {
  // Task management
  TASKS: `${API_URLS.BACKEND_BASE}/api/tasks`,
  TASK_BY_ID: (id) => `${API_URLS.BACKEND_BASE}/api/tasks/${id}`,
  TASK_CLUSTERS: (id) => `${API_URLS.BACKEND_BASE}/api/tasks/${id}/clusters`,
  TASK_LOGS: (id) => `${API_URLS.BACKEND_BASE}/api/tasks/${id}/logs`,
  
  // Workflow management
  WORKFLOWS: `${API_URLS.BACKEND_BASE}/api/workflows`,
  WORKFLOW_BY_ID: (id) => `${API_URLS.BACKEND_BASE}/api/workflows/${id}`,
  
  // Execution
  EXECUTIONS: `${API_URLS.BACKEND_BASE}/api/executions`,
  EXECUTION_BY_ID: (id) => `${API_URLS.BACKEND_BASE}/api/executions/${id}`,
  
  // ------------------------------------------------------------------
  // Pre-defined Action / Scenario Library
  // ------------------------------------------------------------------
  LIBRARY_BASE: `${API_URLS.BACKEND_BASE}/api/library`,
  LIBRARY_CATEGORIES: `${API_URLS.BACKEND_BASE}/api/library/categories`,
  LIBRARY_CATEGORY_BY_ID: (categoryId) =>
    `${API_URLS.BACKEND_BASE}/api/library/categories/${categoryId}`,
  LIBRARY_ACTION_BY_ID: (actionId) =>
    `${API_URLS.BACKEND_BASE}/api/library/actions/${actionId}`,
  
  // Agent control
  AGENT_START: `${API_URLS.AGENT_CONTROL_BASE}/start`,
  AGENT_STOP: `${API_URLS.AGENT_CONTROL_BASE}/stop`,
};

// Feature flags and configuration options
export const CONFIG = {
  // Whether to use mock data when the API is unavailable
  USE_MOCK_FALLBACK: true,
  
  // How long to wait before considering an API request failed (ms)
  API_TIMEOUT: 10000,
  
  // Polling interval for task status updates (ms)
  TASK_STATUS_POLLING_INTERVAL: 5000,
  
  // Maximum number of retries for API requests
  MAX_API_RETRIES: 3,
  
  // Whether to show debug information in the UI
  SHOW_DEBUG_INFO: isDevelopment,
};

// Graph visualization settings
export const GRAPH_CONFIG = {
  NODE_RADIUS: 8,
  LINK_STRENGTH: 0.7,
  CHARGE_STRENGTH: -300,
  LINK_DISTANCE: 100,
  SIMULATION_ALPHA: 0.3,
  COLORS: {
    NODE: '#4285F4',
    LINK: '#aaaaaa',
    SELECTED: '#f59e0b',
    TEXT: '#333333',
  }
};

// Default export for convenience
export default {
  API_URLS,
  ENDPOINTS,
  CONFIG,
  GRAPH_CONFIG,
  isDevelopment,
};
