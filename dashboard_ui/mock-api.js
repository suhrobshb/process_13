/**
 * Mock API Service
 * ---------------
 * Simulates backend API endpoints for dashboard development.
 * Use this during frontend development when the actual backend
 * is not available or to test specific scenarios.
 */

// Configuration
const API_DELAY = 800; // Simulate network delay (ms)
const SIMULATE_ERRORS = false; // Set to true to test error handling

// Sample tasks data
const MOCK_TASKS = [
  {
    id: 1,
    filename: "login_sequence.zip",
    status: "completed",
    created_at: "2025-06-20T14:30:00Z",
    updated_at: "2025-06-20T14:35:22Z",
    workflow_id: null,
    user_id: 1
  },
  {
    id: 2,
    filename: "data_entry_task.zip",
    status: "processing",
    created_at: "2025-06-22T09:15:00Z",
    updated_at: "2025-06-22T09:15:00Z",
    workflow_id: null,
    user_id: 1
  },
  {
    id: 3,
    filename: "report_generation.zip",
    status: "completed",
    created_at: "2025-06-23T16:45:00Z",
    updated_at: "2025-06-23T16:50:12Z",
    workflow_id: 5,
    user_id: 1
  },
  {
    id: 4,
    filename: "email_processing.zip",
    status: "uploaded",
    created_at: "2025-06-25T10:20:00Z",
    updated_at: "2025-06-25T10:20:00Z",
    workflow_id: null,
    user_id: 1
  }
];

// Sample cluster data for each task
const MOCK_CLUSTERS = {
  1: {
    nodes: [
      { id: "1", label: "Open Browser" },
      { id: "2", label: "Navigate to Login" },
      { id: "3", label: "Enter Username" },
      { id: "4", label: "Enter Password" },
      { id: "5", label: "Click Login" },
      { id: "6", label: "Verify Dashboard" }
    ],
    links: [
      { source: "1", target: "2" },
      { source: "2", target: "3" },
      { source: "3", target: "4" },
      { source: "4", target: "5" },
      { source: "5", target: "6" }
    ]
  },
  2: {
    nodes: [
      { id: "1", label: "Open Form" },
      { id: "2", label: "Enter Customer Data" },
      { id: "3", label: "Upload Document" },
      { id: "4", label: "Submit Form" }
    ],
    links: [
      { source: "1", target: "2" },
      { source: "2", target: "3" },
      { source: "3", target: "4" }
    ]
  },
  3: {
    nodes: [
      { id: "1", label: "Open Reports" },
      { id: "2", label: "Select Date Range" },
      { id: "3", label: "Generate Report" },
      { id: "4", label: "Export PDF" },
      { id: "5", label: "Email Report" }
    ],
    links: [
      { source: "1", target: "2" },
      { source: "2", target: "3" },
      { source: "3", target: "4" },
      { source: "3", target: "5" }
    ]
  },
  4: {
    nodes: [
      { id: "1", label: "Check Inbox" },
      { id: "2", label: "Filter Messages" },
      { id: "3", label: "Process Important" },
      { id: "4", label: "Archive Others" }
    ],
    links: [
      { source: "1", target: "2" },
      { source: "2", target: "3" },
      { source: "2", target: "4" }
    ]
  }
};

/**
 * Simulates network delay and optionally generates errors
 * @param {*} data The data to return
 * @returns {Promise} Promise that resolves with the data
 */
function simulateResponse(data) {
  return new Promise((resolve, reject) => {
    setTimeout(() => {
      // Randomly fail some requests if error simulation is enabled
      if (SIMULATE_ERRORS && Math.random() < 0.25) {
        reject(new Error("Simulated API error"));
      } else {
        resolve(data);
      }
    }, API_DELAY);
  });
}

/**
 * Mock API for fetching tasks
 * @returns {Promise<Array>} Promise resolving to array of tasks
 */
export async function fetchTasks() {
  return simulateResponse(MOCK_TASKS);
}

/**
 * Mock API for fetching clusters for a specific task
 * @param {number} taskId The task ID
 * @returns {Promise<Object>} Promise resolving to cluster data
 */
export async function fetchTaskClusters(taskId) {
  const clusters = MOCK_CLUSTERS[taskId];
  if (!clusters) {
    return Promise.reject(new Error(`No clusters found for task ${taskId}`));
  }
  return simulateResponse(clusters);
}

/**
 * Mock API for recording a new task
 * @returns {Promise<Object>} Promise resolving to new task data
 */
export async function recordNewTask() {
  const newTask = {
    id: Math.max(...MOCK_TASKS.map(t => t.id)) + 1,
    filename: `task_${Date.now()}.zip`,
    status: "uploaded",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    workflow_id: null,
    user_id: 1
  };
  
  // Add to mock data
  MOCK_TASKS.push(newTask);
  
  return simulateResponse(newTask);
}

/**
 * Mock API for saving a workflow
 * @param {number} taskId The source task ID
 * @param {string} name The workflow name
 * @returns {Promise<Object>} Promise resolving to workflow data
 */
export async function saveAsWorkflow(taskId, name) {
  return simulateResponse({
    id: Math.floor(Math.random() * 1000),
    name,
    task_id: taskId,
    created_at: new Date().toISOString()
  });
}

// Default export for convenience
export default {
  fetchTasks,
  fetchTaskClusters,
  recordNewTask,
  saveAsWorkflow
};
