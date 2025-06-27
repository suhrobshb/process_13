import React, { useState, useEffect } from 'react';
import { ENDPOINTS } from '../config';

/**
 * WorkflowBrowser Component
 * -------------------------
 * Displays a list of available workflows and provides actions to manage them.
 * 
 * Props:
 * - onSelectWorkflow: Function called when a workflow is selected for editing
 * - onCreateNew: Function called when user wants to create a new workflow
 * - className: Optional additional CSS classes
 */
const WorkflowBrowser = ({ onSelectWorkflow, onCreateNew, className = '' }) => {
  // State for workflows and UI state
  const [workflows, setWorkflows] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionInProgress, setActionInProgress] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  // Fetch workflows on mount
  useEffect(() => {
    fetchWorkflows();
  }, []);

  // Clear success message after 5 seconds
  useEffect(() => {
    if (successMessage) {
      const timer = setTimeout(() => {
        setSuccessMessage(null);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [successMessage]);

  // Fetch workflows from API
  const fetchWorkflows = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await fetch(ENDPOINTS.WORKFLOWS);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch workflows: ${response.statusText}`);
      }
      
      const data = await response.json();
      setWorkflows(data);
    } catch (err) {
      console.error('Error fetching workflows:', err);
      setError('Failed to load workflows. Please try again later.');
    } finally {
      setIsLoading(false);
    }
  };

  // Handle workflow activation/deactivation
  const handleToggleActive = async (workflow) => {
    try {
      setActionInProgress(workflow.id);
      
      const endpoint = workflow.status === 'active' 
        ? `${ENDPOINTS.WORKFLOW_BY_ID(workflow.id)}/deactivate`
        : `${ENDPOINTS.WORKFLOW_BY_ID(workflow.id)}/activate`;
      
      const response = await fetch(endpoint, {
        method: 'POST',
      });
      
      if (!response.ok) {
        throw new Error(`Failed to update workflow status: ${response.statusText}`);
      }
      
      // Update workflow status in the list
      setWorkflows(prevWorkflows => 
        prevWorkflows.map(wf => 
          wf.id === workflow.id 
            ? { ...wf, status: workflow.status === 'active' ? 'draft' : 'active' }
            : wf
        )
      );
      
      setSuccessMessage(`Workflow ${workflow.status === 'active' ? 'deactivated' : 'activated'} successfully`);
    } catch (err) {
      console.error('Error updating workflow status:', err);
      setError(`Failed to update workflow status: ${err.message}`);
    } finally {
      setActionInProgress(null);
    }
  };

  // Handle workflow cloning
  const handleCloneWorkflow = async (workflow) => {
    try {
      setActionInProgress(workflow.id);
      
      const response = await fetch(`${ENDPOINTS.WORKFLOW_BY_ID(workflow.id)}/clone`, {
        method: 'POST',
      });
      
      if (!response.ok) {
        throw new Error(`Failed to clone workflow: ${response.statusText}`);
      }
      
      const clonedWorkflow = await response.json();
      
      // Add the cloned workflow to the list
      setWorkflows(prevWorkflows => [...prevWorkflows, clonedWorkflow]);
      
      setSuccessMessage(`Workflow cloned successfully`);
    } catch (err) {
      console.error('Error cloning workflow:', err);
      setError(`Failed to clone workflow: ${err.message}`);
    } finally {
      setActionInProgress(null);
    }
  };

  // Handle workflow deletion
  const handleDeleteWorkflow = async (workflow) => {
    // Confirm before deleting
    if (!confirm(`Are you sure you want to delete the workflow "${workflow.name}"?`)) {
      return;
    }
    
    try {
      setActionInProgress(workflow.id);
      
      const response = await fetch(ENDPOINTS.WORKFLOW_BY_ID(workflow.id), {
        method: 'DELETE',
      });
      
      if (!response.ok) {
        throw new Error(`Failed to delete workflow: ${response.statusText}`);
      }
      
      // Remove the workflow from the list
      setWorkflows(prevWorkflows => 
        prevWorkflows.filter(wf => wf.id !== workflow.id)
      );
      
      setSuccessMessage(`Workflow deleted successfully`);
    } catch (err) {
      console.error('Error deleting workflow:', err);
      setError(`Failed to delete workflow: ${err.message}`);
    } finally {
      setActionInProgress(null);
    }
  };

  // Format date for display
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  // Get status badge class
  const getStatusBadgeClass = (status) => {
    switch (status) {
      case 'active':
        return 'status-active';
      case 'draft':
        return 'status-draft';
      case 'archived':
        return 'status-archived';
      default:
        return '';
    }
  };

  return (
    <div className={`workflow-browser ${className}`}>
      <div className="browser-header">
        <h2>Workflows</h2>
        <button 
          className="create-button"
          onClick={onCreateNew}
        >
          Create New Workflow
        </button>
      </div>
      
      {/* Error and success messages */}
      {error && (
        <div className="error-message">
          {error}
          <button className="dismiss-button" onClick={() => setError(null)}>✕</button>
        </div>
      )}
      
      {successMessage && (
        <div className="success-message">
          {successMessage}
          <button className="dismiss-button" onClick={() => setSuccessMessage(null)}>✕</button>
        </div>
      )}
      
      {/* Loading indicator */}
      {isLoading && (
        <div className="loading-indicator">
          Loading workflows...
        </div>
      )}
      
      {/* Workflows list */}
      {!isLoading && workflows.length === 0 ? (
        <div className="empty-state">
          <p>No workflows found. Create your first workflow to get started.</p>
          <button className="create-button" onClick={onCreateNew}>
            Create New Workflow
          </button>
        </div>
      ) : (
        <div className="workflows-list">
          <table className="workflows-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Status</th>
                <th>Created</th>
                <th>Updated</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {workflows.map(workflow => (
                <tr key={workflow.id} className="workflow-row">
                  <td className="workflow-name">{workflow.name}</td>
                  <td>
                    <span className={`status-badge ${getStatusBadgeClass(workflow.status)}`}>
                      {workflow.status}
                    </span>
                  </td>
                  <td>{formatDate(workflow.created_at)}</td>
                  <td>{formatDate(workflow.updated_at)}</td>
                  <td className="actions-cell">
                    <button
                      className="action-button edit-button"
                      onClick={() => onSelectWorkflow(workflow)}
                      title="Edit workflow"
                    >
                      Edit
                    </button>
                    
                    <button
                      className={`action-button ${workflow.status === 'active' ? 'deactivate-button' : 'activate-button'}`}
                      onClick={() => handleToggleActive(workflow)}
                      disabled={actionInProgress === workflow.id}
                      title={workflow.status === 'active' ? 'Deactivate workflow' : 'Activate workflow'}
                    >
                      {workflow.status === 'active' ? 'Deactivate' : 'Activate'}
                    </button>
                    
                    <button
                      className="action-button clone-button"
                      onClick={() => handleCloneWorkflow(workflow)}
                      disabled={actionInProgress === workflow.id}
                      title="Clone workflow"
                    >
                      Clone
                    </button>
                    
                    <button
                      className="action-button delete-button"
                      onClick={() => handleDeleteWorkflow(workflow)}
                      disabled={actionInProgress === workflow.id}
                      title="Delete workflow"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      
      <style jsx>{`
        .workflow-browser {
          background: white;
          border-radius: 6px;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
          padding: 20px;
        }
        
        .browser-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
        }
        
        .browser-header h2 {
          margin: 0;
          font-size: 20px;
          font-weight: 600;
        }
        
        .create-button {
          padding: 8px 16px;
          background: #4285F4;
          color: white;
          border: none;
          border-radius: 4px;
          font-weight: 500;
          cursor: pointer;
          transition: background-color 0.2s;
        }
        
        .create-button:hover {
          background: #3367d6;
        }
        
        .error-message,
        .success-message {
          padding: 12px 16px;
          border-radius: 4px;
          margin-bottom: 16px;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        
        .error-message {
          background: #ffebee;
          color: #d32f2f;
        }
        
        .success-message {
          background: #e8f5e9;
          color: #388e3c;
        }
        
        .dismiss-button {
          background: none;
          border: none;
          color: inherit;
          cursor: pointer;
          font-size: 16px;
        }
        
        .loading-indicator {
          text-align: center;
          padding: 20px;
          color: #666;
        }
        
        .empty-state {
          text-align: center;
          padding: 40px 20px;
          color: #666;
        }
        
        .empty-state p {
          margin-bottom: 20px;
        }
        
        .workflows-table {
          width: 100%;
          border-collapse: collapse;
        }
        
        .workflows-table th,
        .workflows-table td {
          padding: 12px 16px;
          text-align: left;
          border-bottom: 1px solid #eee;
        }
        
        .workflows-table th {
          font-weight: 600;
          color: #333;
          background: #f5f5f5;
        }
        
        .workflow-row:hover {
          background: #f9f9f9;
        }
        
        .workflow-name {
          font-weight: 500;
        }
        
        .status-badge {
          display: inline-block;
          padding: 4px 8px;
          border-radius: 12px;
          font-size: 12px;
          font-weight: 500;
          text-transform: uppercase;
        }
        
        .status-active {
          background: #c8e6c9;
          color: #388e3c;
        }
        
        .status-draft {
          background: #bbdefb;
          color: #1976d2;
        }
        
        .status-archived {
          background: #e0e0e0;
          color: #616161;
        }
        
        .actions-cell {
          display: flex;
          gap: 8px;
        }
        
        .action-button {
          padding: 6px 12px;
          border: none;
          border-radius: 4px;
          font-size: 13px;
          cursor: pointer;
          transition: background-color 0.2s;
        }
        
        .edit-button {
          background: #2196f3;
          color: white;
        }
        
        .edit-button:hover {
          background: #1976d2;
        }
        
        .activate-button {
          background: #4caf50;
          color: white;
        }
        
        .activate-button:hover {
          background: #388e3c;
        }
        
        .deactivate-button {
          background: #ff9800;
          color: white;
        }
        
        .deactivate-button:hover {
          background: #f57c00;
        }
        
        .clone-button {
          background: #9c27b0;
          color: white;
        }
        
        .clone-button:hover {
          background: #7b1fa2;
        }
        
        .delete-button {
          background: #f44336;
          color: white;
        }
        
        .delete-button:hover {
          background: #d32f2f;
        }
        
        .action-button:disabled {
          background: #ccc;
          cursor: not-allowed;
        }
      `}</style>
    </div>
  );
};

export default WorkflowBrowser;
