import React, { useState, useEffect, useMemo } from 'react';

// --- Mock Data (replace with API call) ---
const mockWorkflows = [
  {
    id: 1,
    name: 'Automated Invoice Processing',
    description: 'Processes vendor invoices from the accounting inbox.',
    status: 'active',
    confidence: 0.95,
    lastRun: { date: '2025-06-27 10:30 AM', status: 'completed' },
    successRate: 1.0,
    tags: ['accounting', 'finance'],
    createdBy: 'admin_user',
    updatedAt: '2025-06-27 09:15:00Z',
  },
  {
    id: 2,
    name: 'AI-Assisted Contract Review',
    description: 'Analyzes new contracts against company legal playbook.',
    status: 'active',
    confidence: 0.88,
    lastRun: { date: '2025-06-26 15:45 PM', status: 'failed' },
    successRate: 0.92,
    tags: ['legal', 'compliance'],
    createdBy: 'legal_team',
    updatedAt: '2025-06-25 11:00:00Z',
  },
  {
    id: 3,
    name: 'New Employee Onboarding',
    description: 'A workflow for setting up new hire accounts and access.',
    status: 'draft',
    confidence: 0.72,
    lastRun: null,
    successRate: null,
    tags: ['hr', 'it'],
    createdBy: 'hr_admin',
    updatedAt: '2025-06-24 18:20:00Z',
  },
  {
    id: 4,
    name: 'Daily Social Media Posting',
    description: 'Generates and posts daily updates to social channels.',
    status: 'archived',
    confidence: 0.98,
    lastRun: { date: '2025-05-30 09:00 AM', status: 'completed' },
    successRate: 1.0,
    tags: ['marketing', 'social'],
    createdBy: 'marketing_lead',
    updatedAt: '2025-05-30 09:01:00Z',
  },
];

// --- Helper Components ---

const StatusBadge = ({ status }) => {
  const styles = {
    active: 'bg-green-100 text-green-800',
    draft: 'bg-blue-100 text-blue-800',
    archived: 'bg-gray-100 text-gray-800',
  };
  return (
    <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${styles[status] || styles.archived}`}>
      {status}
    </span>
  );
};

const ConfidenceBar = ({ score }) => {
  let color = 'bg-green-500';
  if (score < 0.9) color = 'bg-yellow-500';
  if (score < 0.75) color = 'bg-red-500';

  return (
    <div className="w-full bg-gray-200 rounded-full h-2.5">
      <div className={`${color} h-2.5 rounded-full`} style={{ width: `${score * 100}%` }}></div>
    </div>
  );
};

const ActionButton = ({ onClick, children, className, title }) => (
  <button onClick={onClick} title={title} className={`p-1.5 rounded hover:bg-gray-200 ${className}`}>
    {children}
  </button>
);

// --- Main Component ---

const WorkflowBrowser = ({ onSelectWorkflow, onCreateNew }) => {
  const [workflows, setWorkflows] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [sortBy, setSortBy] = useState({ field: 'updatedAt', direction: 'desc' });

  // Fetch workflows from API on mount
  useEffect(() => {
    const fetchWorkflows = async () => {
      try {
        setIsLoading(true);
        // Replace with actual API call, e.g., await fetch('/api/workflows');
        await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate network delay
        setWorkflows(mockWorkflows);
        setError(null);
      } catch (err) {
        setError('Failed to load workflows. Please try again later.');
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchWorkflows();
  }, []);

  // Memoized filtering and sorting logic
  const filteredAndSortedWorkflows = useMemo(() => {
    return workflows
      .filter(wf => {
        const matchesSearch = wf.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                              wf.description.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesStatus = statusFilter === 'all' || wf.status === statusFilter;
        return matchesSearch && matchesStatus;
      })
      .sort((a, b) => {
        const fieldA = a[sortBy.field];
        const fieldB = b[sortBy.field];
        let comparison = 0;
        if (fieldA > fieldB) {
          comparison = 1;
        } else if (fieldA < fieldB) {
          comparison = -1;
        }
        return sortBy.direction === 'desc' ? comparison * -1 : comparison;
      });
  }, [workflows, searchTerm, statusFilter, sortBy]);

  const handleSort = (field) => {
    const direction = sortBy.field === field && sortBy.direction === 'asc' ? 'desc' : 'asc';
    setSortBy({ field, direction });
  };
  
  // --- Render Functions ---

  const renderTableHeader = () => (
    <thead className="bg-gray-50">
      <tr>
        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer" onClick={() => handleSort('name')}>
          Workflow
        </th>
        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer" onClick={() => handleSort('status')}>
          Status
        </th>
        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer" onClick={() => handleSort('confidence')}>
          AI Confidence
        </th>
        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer" onClick={() => handleSort('lastRun')}>
          Last Run
        </th>
        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer" onClick={() => handleSort('successRate')}>
          Success Rate
        </th>
        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
          Actions
        </th>
      </tr>
    </thead>
  );

  const renderWorkflowRow = (workflow) => (
    <tr key={workflow.id} className="bg-white hover:bg-gray-50">
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="text-sm font-medium text-gray-900">{workflow.name}</div>
        <div className="text-sm text-gray-500">{workflow.description}</div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <StatusBadge status={workflow.status} />
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="flex items-center">
          <div className="w-24 mr-2">
            <ConfidenceBar score={workflow.confidence} />
          </div>
          <div className="text-sm text-gray-900">{`${Math.round(workflow.confidence * 100)}%`}</div>
        </div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
        {workflow.lastRun ? (
          <div>
            <div>{workflow.lastRun.date}</div>
            <StatusBadge status={workflow.lastRun.status} />
          </div>
        ) : 'Never run'}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
        {workflow.successRate !== null ? `${(workflow.successRate * 100).toFixed(1)}%` : 'N/A'}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
        <div className="flex items-center space-x-2">
          <ActionButton onClick={() => onSelectWorkflow(workflow)} title="Edit Workflow">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-600" viewBox="0 0 20 20" fill="currentColor"><path d="M17.414 2.586a2 2 0 00-2.828 0L7 10.172V13h2.828l7.586-7.586a2 2 0 000-2.828z" /><path fillRule="evenodd" d="M2 6a2 2 0 012-2h4a1 1 0 010 2H4v10h10v-4a1 1 0 112 0v4a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" clipRule="evenodd" /></svg>
          </ActionButton>
          <ActionButton onClick={() => alert(`Running workflow ${workflow.id}`)} title="Run Workflow">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-green-600" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" /></svg>
          </ActionButton>
          <ActionButton onClick={() => alert(`Cloning workflow ${workflow.id}`)} title="Clone Workflow">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-600" viewBox="0 0 20 20" fill="currentColor"><path d="M7 9a2 2 0 012-2h6a2 2 0 012 2v6a2 2 0 01-2 2H9a2 2 0 01-2-2V9z" /><path d="M5 3a2 2 0 00-2 2v6a2 2 0 002 2V5h6a2 2 0 00-2-2H5z" /></svg>
          </ActionButton>
          <ActionButton onClick={() => alert(`Deleting workflow ${workflow.id}`)} title="Delete Workflow">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-red-600" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" /></svg>
          </ActionButton>
        </div>
      </td>
    </tr>
  );

  if (isLoading) {
    return <div className="p-8 text-center">Loading workflows...</div>;
  }

  if (error) {
    return <div className="p-8 text-center text-red-500">{error}</div>;
  }

  return (
    <div className="p-8 bg-gray-50 min-h-full">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Workflow Management</h1>
        <button
          onClick={onCreateNew}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
        >
          Create New Workflow
        </button>
      </div>

      {/* Toolbar */}
      <div className="mb-4 flex space-x-4">
        <input
          type="text"
          placeholder="Search workflows..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="flex-grow shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block sm:text-sm border-gray-300 rounded-md"
        >
          <option value="all">All Statuses</option>
          <option value="active">Active</option>
          <option value="draft">Draft</option>
          <option value="archived">Archived</option>
        </select>
      </div>

      {/* Workflow Table */}
      <div className="flex flex-col">
        <div className="-my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
          <div className="py-2 align-middle inline-block min-w-full sm:px-6 lg:px-8">
            <div className="shadow overflow-hidden border-b border-gray-200 sm:rounded-lg">
              <table className="min-w-full divide-y divide-gray-200">
                {renderTableHeader()}
                <tbody className="bg-white divide-y divide-gray-200">
                  {filteredAndSortedWorkflows.length > 0 ? (
                    filteredAndSortedWorkflows.map(renderWorkflowRow)
                  ) : (
                    <tr>
                      <td colSpan="6" className="px-6 py-12 text-center text-gray-500">
                        No workflows found.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default WorkflowBrowser;
