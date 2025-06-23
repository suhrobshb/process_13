'use client';

import { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';

// Dynamically import the graph component to avoid SSR issues with browser-only APIs
const TaskRelationshipGraph = dynamic(
  () => import('../graphs/TaskRelationshipGraph'),
  { ssr: false }
);

export default function Dashboard() {
  const [tasks, setTasks] = useState([]);
  const [selectedTask, setSelectedTask] = useState(null);
  const [clusters, setClusters] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Fetch tasks on component mount
  useEffect(() => {
    async function fetchTasks() {
      try {
        const response = await fetch('http://localhost:8000/api/tasks/');
        if (!response.ok) throw new Error('Failed to fetch tasks');
        const data = await response.json();
        setTasks(data);
      } catch (err) {
        // log the full error so we can diagnose network / CORS issues
        // without confusing the user with implementation details.
        /* eslint-disable no-console */
        console.error('Fetch Error (tasks):', err);
        /* eslint-enable no-console */
        setError('Failed to fetch tasks. See console for details.');
      }
    }
    
    fetchTasks();
  }, []);

  // Fetch clusters when a task is selected
  async function loadTaskClusters(taskId) {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`http://localhost:8000/api/tasks/${taskId}/clusters`);
      if (!response.ok) throw new Error('Failed to fetch clusters');
      
      const data = await response.json();
      setClusters(data);
      setSelectedTask(taskId);
    } catch (err) {
      setError('Error loading clusters: ' + err.message);
      setClusters([]);
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
      </header>

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
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <p className="text-gray-500">Loading clusters...</p>
            </div>
          ) : selectedTask ? (
            <>
              <h2 className="text-xl font-semibold mb-4">Task Relationship Graph</h2>
              <div className="border rounded p-4 h-[600px]">
                <TaskRelationshipGraph clusters={clusters} />
              </div>
              <div className="mt-4 flex justify-end">
                <button className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded mr-2">
                  Save as Workflow
                </button>
              </div>
            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <p>Select a task from the sidebar to view its clusters</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
