'use client';

import { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';

// Mock helpers – will be used only if real API is unreachable
import {
  fetchTasks as mockFetchTasks,
  fetchTaskClusters as mockFetchTaskClusters
} from '../mock-api';

// Centralised API endpoints
import { ENDPOINTS } from '../config';

// Dynamically import the graph component to avoid SSR issues with browser-only APIs
const TaskRelationshipGraph = dynamic(
  () => import('../graphs/TaskRelationshipGraph'),
  { ssr: false }
);

// Visual workflow editor (needs browser APIs, so load dynamically)
const WorkflowEditor = dynamic(
  () => import('../workflow_editor/WorkflowEditor'),
  { ssr: false }
);
// Workflows browser panel (lazy-loaded)
const WorkflowBrowser = dynamic(
  () => import('../workflow_editor/WorkflowBrowser'),
  { ssr: false }
);
export default function Dashboard() {
  const [tasks, setTasks] = useState([]);
  const [selectedTask, setSelectedTask] = useState(null);
  const [clusters, setClusters] = useState([]);
  const [workflowData, setWorkflowData] = useState(null); // data of workflow being edited
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [apiSource, setApiSource] = useState('live'); // 'live' | 'mock'
  const [activeTab, setActiveTab] = useState('tasks'); // 'tasks' | 'editor' | 'workflows'

  // Fetch tasks on component mount
  useEffect(() => {
    async function fetchTasks() {
      try {
        const response = await fetch(ENDPOINTS.TASKS);
        if (!response.ok) throw new Error('Failed to fetch tasks');
        const data = await response.json();
        setTasks(data);
        setApiSource('live');
      } catch (err) {
        // log the full error so we can diagnose network / CORS issues
        // without confusing the user with implementation details.
        /* eslint-disable no-console */
        console.error('Fetch Error (tasks):', err);
        /* eslint-enable no-console */
        // Fallback to mock API
        try {
          const data = await mockFetchTasks();
          setTasks(data);
          setApiSource('mock');
        } catch (mockErr) {
          console.error('Mock Fetch Error (tasks):', mockErr);
          setError('Failed to fetch tasks from both live and mock APIs.');
        }
      }
    }
    
    fetchTasks();
  }, []);

  // Fetch clusters when a task is selected
  async function loadTaskClusters(taskId) {
    setLoading(true);
    setError(null);
    
    try {
      let data;
      if (apiSource === 'live') {
        const response = await fetch(ENDPOINTS.TASK_CLUSTERS(taskId));
        if (!response.ok) throw new Error('Failed to fetch clusters');
        data = await response.json();
      } else {
        data = await mockFetchTaskClusters(taskId);
      }
      setClusters(data);
      setSelectedTask(taskId);
    } catch (err) {
      console.error('Cluster fetch error:', err);
      if (apiSource === 'live') {
        // Attempt fallback to mock clusters
        try {
          const data = await mockFetchTaskClusters(taskId);
          setClusters(data);
          setSelectedTask(taskId);
          setApiSource('mock');
        } catch (mockErr) {
          setError('Error loading clusters: ' + mockErr.message);
          setClusters([]);
        }
      } else {
        setError('Error loading clusters: ' + err.message);
        setClusters([]);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container mx-auto p-4">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-center mb-2">AI Engine Dashboard</h1>
        <p className="text-center text-gray-600">
          View and edit your recorded tasks and workflows
        </p>
        <p className="text-center text-xs mt-2 text-gray-400">
          API Source:&nbsp;
          <span className={apiSource === 'live' ? 'text-green-600' : 'text-yellow-600'}>
            {apiSource === 'live' ? 'Live Backend' : 'Mock'}
          </span>
        </p>
      </header>

      {/* -------- Tabs -------- */}
      <div className="mb-4 border-b flex gap-6">
        <button
          className={`pb-2 ${
            activeTab === 'tasks'
              ? 'border-b-2 border-blue-600 text-blue-600'
              : 'text-gray-600 hover:text-gray-800'
          }`}
          onClick={() => setActiveTab('tasks')}
        >
          Task View
        </button>
        <button
          className={`pb-2 ${
            activeTab === 'editor'
              ? 'border-b-2 border-blue-600 text-blue-600'
              : selectedTask
              ? 'text-gray-600 hover:text-gray-800'
              : 'text-gray-400 cursor-not-allowed'
          }`}
          onClick={() => selectedTask && setActiveTab('editor')}
          disabled={!selectedTask}
        >
          Workflow Editor
        </button>
        <button
          className={`pb-2 ${
            activeTab === 'workflows'
              ? 'border-b-2 border-blue-600 text-blue-600'
              : 'text-gray-600 hover:text-gray-800'
          }`}
          onClick={() => setActiveTab('workflows')}
        >
          Workflows
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* Task List Sidebar */}
        <div className="md:col-span-1 bg-white p-4 rounded shadow">
          <h2 className="text-xl font-semibold mb-4">Recorded Tasks</h2>
          
          {error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
              {error}
            </div>
          )}
          
          {tasks.length === 0 ? (
            <p className="text-gray-500">No tasks found. Record a new task to get started.</p>
          ) : (
            <ul className="space-y-2">
              {tasks.map(task => (
                <li key={task.id}>
                  <button
                    onClick={() => loadTaskClusters(task.id)}
                    className={`w-full text-left px-3 py-2 rounded ${
                      selectedTask === task.id ? 'bg-blue-100 text-blue-800' : 'hover:bg-gray-100'
                    }`}
                  >
                    {task.filename}
                    <span className={`ml-2 text-xs px-2 py-1 rounded ${
                      task.status === 'completed' ? 'bg-green-100 text-green-800' : 
                      task.status === 'processing' ? 'bg-yellow-100 text-yellow-800' : 
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {task.status}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          
          <div className="mt-6">
            <a 
              href="/record_test.html" 
              target="_blank"
              className="block w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded text-center"
            >
              Record New Task
            </a>
          </div>
        </div>

        {/* Main Content Area */}
        <div className="md:col-span-3 bg-white p-4 rounded shadow min-h-[500px]">
          {activeTab === 'tasks' && loading ? (
            <div className="flex items-center justify-center h-full">
              <p className="text-gray-500">Loading clusters...</p>
            </div>
          ) : activeTab === 'tasks' && selectedTask ? (
            <>
              <h2 className="text-xl font-semibold mb-4">Task Relationship Graph</h2>
              <div className="border rounded p-4 h-[600px]">
                <TaskRelationshipGraph clusters={clusters} />
              </div>
              <div className="mt-4 flex justify-end">
                <button
                  className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded mr-2"
                  onClick={() => setActiveTab('editor')}
                >
                  Open Workflow Editor
                </button>
              </div>
            </>
          ) : activeTab === 'tasks' ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <p>Select a task from the sidebar to view its clusters</p>
            </div>
          ) : (
            activeTab === 'workflows' ? (
              /* Workflows tab */
              <WorkflowBrowser
                onSelectWorkflow={(wf) => {
                  setWorkflowData(wf);
                  setSelectedTask(null);
                  setActiveTab('editor');
                }}
                onCreateNew={() => {
                  setWorkflowData(null);
                  setSelectedTask(null);
                  setActiveTab('editor');
                }}
              />
            ) : (
              /* Workflow Editor Tab */
              <WorkflowEditor
                taskId={selectedTask}
                initialData={workflowData}
              />
            )
          )}
        </div>
      </div>
    </div>
  );
}
