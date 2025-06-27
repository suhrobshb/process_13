import React, { useState, useEffect, useRef } from 'react';
import { ENDPOINTS } from '../config';

/**
 * ExecutionMonitor Component
 * --------------------------
 * Monitors and displays the status and details of a workflow execution.
 * Provides real-time updates using server-sent events and allows for
 * interaction with the execution (approvals, retries, rollbacks).
 * 
 * Props:
 * - executionId: ID of the execution to monitor
 * - workflowId: ID of the workflow being executed
 * - onClose: Function to call when the monitor is closed
 */
const ExecutionMonitor = ({ executionId, workflowId, onClose }) => {
  // State for execution data and UI
  const [execution, setExecution] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [approvalData, setApprovalData] = useState({
    showApprovalForm: false,
    approvalId: null,
    comments: '',
  });
  
  // Ref for SSE connection
  const eventSourceRef = useRef(null);
  
  // Fetch initial execution data
  useEffect(() => {
    const fetchExecution = async () => {
      try {
        setLoading(true);
        const response = await fetch(ENDPOINTS.EXECUTION_BY_ID(executionId));
        
        if (!response.ok) {
          throw new Error(`Failed to fetch execution: ${response.statusText}`);
        }
        
        const data = await response.json();
        setExecution(data);
      } catch (err) {
        console.error('Error fetching execution:', err);
        setError(`Failed to load execution details: ${err.message}`);
      } finally {
        setLoading(false);
      }
    };
    
    if (executionId) {
      fetchExecution();
    }
  }, [executionId]);
  
  // Set up SSE for real-time updates
  useEffect(() => {
    if (!executionId) return;
    
    // Close any existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    
    // Create new EventSource connection
    const eventSource = new EventSource(ENDPOINTS.EXECUTION_BY_ID(executionId) + '/stream');
    eventSourceRef.current = eventSource;
    
    // Handle incoming events
    eventSource.addEventListener('status', (event) => {
      try {
        const data = JSON.parse(event.data);
        setExecution(prevExecution => {
          if (!prevExecution) return data;
          
          return {
            ...prevExecution,
            status: data.status,
            updated_at: data.updated_at,
            error: data.error,
            result: data.result
          };
        });
        
        // If execution is complete or failed, close the connection
        if (data.status === 'completed' || data.status === 'failed') {
          eventSource.close();
        }
      } catch (err) {
        console.error('Error parsing SSE data:', err);
      }
    });
    
    // Handle connection error
    eventSource.onerror = (err) => {
      console.error('SSE connection error:', err);
      eventSource.close();
    };
    
    // Cleanup on unmount
    return () => {
      eventSource.close();
    };
  }, [executionId]);
  
  // Handle approval submission
  const handleApproval = async (approved) => {
    try {
      const response = await fetch(`${ENDPOINTS.EXECUTION_BY_ID(executionId)}/approve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          approval_id: approvalData.approvalId,
          approved,
          comments: approvalData.comments,
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to submit approval: ${response.statusText}`);
      }
      
      // Reset approval form
      setApprovalData({
        showApprovalForm: false,
        approvalId: null,
        comments: '',
      });
      
      // Refresh execution data
      const data = await response.json();
      if (data.execution) {
        setExecution(data.execution);
      }
    } catch (err) {
      console.error('Error submitting approval:', err);
      setError(`Failed to submit approval: ${err.message}`);
    }
  };
  
  // Handle retry for failed executions
  const handleRetry = async () => {
    try {
      const response = await fetch(`${ENDPOINTS.EXECUTION_BY_ID(executionId)}/retry`, {
        method: 'POST',
      });
      
      if (!response.ok) {
        throw new Error(`Failed to retry execution: ${response.statusText}`);
      }
      
      // Close this monitor and let the caller know to refresh
      onClose();
    } catch (err) {
      console.error('Error retrying execution:', err);
      setError(`Failed to retry execution: ${err.message}`);
    }
  };
  
  // Handle rollback for executions
  const handleRollback = async () => {
    try {
      const response = await fetch(`${ENDPOINTS.EXECUTION_BY_ID(executionId)}/rollback`, {
        method: 'POST',
      });
      
      if (!response.ok) {
        throw new Error(`Failed to rollback execution: ${response.statusText}`);
      }
      
      // Refresh execution data
      const data = await response.json();
      setExecution(prevExecution => ({
        ...prevExecution,
        status: data.status,
      }));
    } catch (err) {
      console.error('Error rolling back execution:', err);
      setError(`Failed to rollback execution: ${err.message}`);
    }
  };
  
  // Show approval form if needed
  const showApprovalForm = (approvalId) => {
    setApprovalData({
      showApprovalForm: true,
      approvalId,
      comments: '',
    });
  };
  
  // Handle comments change in approval form
  const handleCommentsChange = (e) => {
    setApprovalData(prev => ({
      ...prev,
      comments: e.target.value,
    }));
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
      case 'running':
        return 'status-running';
      case 'completed':
        return 'status-completed';
      case 'failed':
        return 'status-failed';
      case 'waiting_approval':
        return 'status-waiting';
      default:
        return 'status-pending';
    }
  };
  
  // Render step results
  const renderStepResults = (results) => {
    if (!results) return null;
    
    return (
      <div className="step-results">
        {Object.entries(results).map(([stepId, result]) => (
          <div key={stepId} className="step-result">
            <div className="step-header">
              <span className="step-id">{stepId}</span>
              <span className={`step-status ${result.success ? 'success' : 'error'}`}>
                {result.success ? 'Success' : 'Failed'}
              </span>
            </div>
            
            {result.error && (
              <div className="step-error">
                <strong>Error:</strong> {result.error}
              </div>
            )}
            
            {result.result && (
              <div className="step-output">
                <div className="output-header">Output:</div>
                <pre className="output-content">
                  {JSON.stringify(result.result, null, 2)}
                </pre>
              </div>
            )}
            
            {/* Show approval button if this step is waiting for approval */}
            {result.result && result.result.status === 'pending' && result.result.approval_id && (
              <button
                className="approve-button"
                onClick={() => showApprovalForm(result.result.approval_id)}
              >
                Approve/Reject
              </button>
            )}
          </div>
        ))}
      </div>
    );
  };
  
  // Render approval form
  const renderApprovalForm = () => {
    if (!approvalData.showApprovalForm) return null;
    
    return (
      <div className="approval-form">
        <h4>Approval Request</h4>
        <div className="form-group">
          <label htmlFor="comments">Comments:</label>
          <textarea
            id="comments"
            value={approvalData.comments}
            onChange={handleCommentsChange}
            placeholder="Enter any comments or feedback"
            rows={4}
          />
        </div>
        <div className="button-group">
          <button
            className="approve-button"
            onClick={() => handleApproval(true)}
          >
            Approve
          </button>
          <button
            className="reject-button"
            onClick={() => handleApproval(false)}
          >
            Reject
          </button>
          <button
            className="cancel-button"
            onClick={() => setApprovalData(prev => ({ ...prev, showApprovalForm: false }))}
          >
            Cancel
          </button>
        </div>
      </div>
    );
  };
  
  // Main render
  if (loading && !execution) {
    return (
      <div className="execution-monitor loading">
        <div className="loading-spinner">Loading execution details...</div>
      </div>
    );
  }
  
  if (error && !execution) {
    return (
      <div className="execution-monitor error">
        <div className="error-message">{error}</div>
        <button className="close-button" onClick={onClose}>
          Close
        </button>
      </div>
    );
  }
  
  if (!execution) {
    return (
      <div className="execution-monitor error">
        <div className="error-message">No execution data available</div>
        <button className="close-button" onClick={onClose}>
          Close
        </button>
      </div>
    );
  }
  
  return (
    <div className="execution-monitor">
      <div className="monitor-header">
        <h3>Workflow Execution #{executionId}</h3>
        <button className="close-button" onClick={onClose}>
          ✕
        </button>
      </div>
      
      {error && (
        <div className="error-message">{error}</div>
      )}
      
      <div className="execution-details">
        <div className="detail-row">
          <span className="detail-label">Status:</span>
          <span className={`status-badge ${getStatusBadgeClass(execution.status)}`}>
            {execution.status}
          </span>
        </div>
        
        <div className="detail-row">
          <span className="detail-label">Started:</span>
          <span className="detail-value">{formatDate(execution.started_at)}</span>
        </div>
        
        {execution.completed_at && (
          <div className="detail-row">
            <span className="detail-label">Completed:</span>
            <span className="detail-value">{formatDate(execution.completed_at)}</span>
          </div>
        )}
        
        {execution.error && (
          <div className="detail-row error">
            <span className="detail-label">Error:</span>
            <span className="detail-value error-text">{execution.error}</span>
          </div>
        )}
      </div>
      
      {/* Action buttons based on execution status */}
      <div className="execution-actions">
        {execution.status === 'failed' && (
          <button className="retry-button" onClick={handleRetry}>
            Retry Execution
          </button>
        )}
        
        {(execution.status === 'running' || execution.status === 'failed') && (
          <button className="rollback-button" onClick={handleRollback}>
            Rollback Execution
          </button>
        )}
        
        {execution.status === 'completed' && (
          <button
            className="new-execution-button"
            onClick={() => {
              // Trigger a new execution of the same workflow
              fetch(`${ENDPOINTS.WORKFLOW_BY_ID(workflowId)}/trigger`, {
                method: 'POST',
              })
                .then(response => {
                  if (!response.ok) throw new Error('Failed to trigger workflow');
                  return response.json();
                })
                .then(() => {
                  onClose(); // Close this monitor after triggering
                })
                .catch(err => {
                  console.error('Error triggering workflow:', err);
                  setError(`Failed to trigger workflow: ${err.message}`);
                });
            }}
          >
            Run Again
          </button>
        )}
      </div>
      
      {/* Show approval form if needed */}
      {renderApprovalForm()}
      
      {/* Results section */}
      <div className="results-section">
        <h4>Execution Results</h4>
        {execution.result ? (
          renderStepResults(execution.result.results)
        ) : (
          <div className="no-results">No results available yet</div>
        )}
      </div>
      
      <style jsx>{`
        .execution-monitor {
          background: white;
          border-radius: 6px;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
          padding: 16px;
          width: 100%;
          max-width: 800px;
          max-height: 80vh;
          overflow-y: auto;
        }
        
        .monitor-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
          border-bottom: 1px solid #eee;
          padding-bottom: 8px;
        }
        
        .monitor-header h3 {
          margin: 0;
          font-size: 18px;
          font-weight: 600;
        }
        
        .close-button {
          background: none;
          border: none;
          cursor: pointer;
          font-size: 16px;
          color: #666;
        }
        
        .error-message {
          color: #d32f2f;
          padding: 8px 12px;
          background: #ffebee;
          border-radius: 4px;
          margin-bottom: 16px;
        }
        
        .execution-details {
          margin-bottom: 20px;
        }
        
        .detail-row {
          display: flex;
          margin-bottom: 8px;
        }
        
        .detail-label {
          font-weight: 600;
          width: 100px;
          flex-shrink: 0;
        }
        
        .detail-value {
          flex-grow: 1;
        }
        
        .error-text {
          color: #d32f2f;
        }
        
        .status-badge {
          display: inline-block;
          padding: 4px 8px;
          border-radius: 12px;
          font-size: 12px;
          font-weight: 600;
          text-transform: uppercase;
        }
        
        .status-pending {
          background: #e0e0e0;
          color: #616161;
        }
        
        .status-running {
          background: #bbdefb;
          color: #1976d2;
        }
        
        .status-completed {
          background: #c8e6c9;
          color: #388e3c;
        }
        
        .status-failed {
          background: #ffcdd2;
          color: #d32f2f;
        }
        
        .status-waiting {
          background: #fff9c4;
          color: #f57f17;
        }
        
        .execution-actions {
          display: flex;
          gap: 10px;
          margin-bottom: 20px;
        }
        
        .retry-button,
        .rollback-button,
        .new-execution-button {
          padding: 8px 16px;
          border: none;
          border-radius: 4px;
          font-weight: 500;
          cursor: pointer;
        }
        
        .retry-button {
          background: #4caf50;
          color: white;
        }
        
        .rollback-button {
          background: #ff9800;
          color: white;
        }
        
        .new-execution-button {
          background: #2196f3;
          color: white;
        }
        
        .results-section {
          margin-top: 20px;
        }
        
        .results-section h4 {
          margin-top: 0;
          margin-bottom: 12px;
          font-size: 16px;
          font-weight: 600;
        }
        
        .no-results {
          color: #757575;
          font-style: italic;
        }
        
        .step-results {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        
        .step-result {
          border: 1px solid #e0e0e0;
          border-radius: 4px;
          padding: 12px;
        }
        
        .step-header {
          display: flex;
          justify-content: space-between;
          margin-bottom: 8px;
        }
        
        .step-id {
          font-weight: 600;
        }
        
        .step-status {
          padding: 2px 6px;
          border-radius: 10px;
          font-size: 12px;
        }
        
        .step-status.success {
          background: #c8e6c9;
          color: #388e3c;
        }
        
        .step-status.error {
          background: #ffcdd2;
          color: #d32f2f;
        }
        
        .step-error {
          margin-top: 8px;
          color: #d32f2f;
          padding: 8px;
          background: #ffebee;
          border-radius: 4px;
        }
        
        .step-output {
          margin-top: 8px;
        }
        
        .output-header {
          font-weight: 500;
          margin-bottom: 4px;
        }
        
        .output-content {
          background: #f5f5f5;
          padding: 8px;
          border-radius: 4px;
          overflow-x: auto;
          font-size: 13px;
          max-height: 200px;
          overflow-y: auto;
        }
        
        .approve-button {
          margin-top: 12px;
          padding: 6px 12px;
          background: #4caf50;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
        }
        
        .approval-form {
          margin-top: 20px;
          padding: 16px;
          background: #f5f5f5;
          border-radius: 4px;
        }
        
        .approval-form h4 {
          margin-top: 0;
          margin-bottom: 12px;
        }
        
        .form-group {
          margin-bottom: 16px;
        }
        
        .form-group label {
          display: block;
          margin-bottom: 8px;
          font-weight: 500;
        }
        
        .form-group textarea {
          width: 100%;
          padding: 8px;
          border: 1px solid #ddd;
          border-radius: 4px;
        }
        
        .button-group {
          display: flex;
          gap: 10px;
        }
        
        .approve-button,
        .reject-button,
        .cancel-button {
          padding: 8px 16px;
          border: none;
          border-radius: 4px;
          font-weight: 500;
          cursor: pointer;
        }
        
        .approve-button {
          background: #4caf50;
          color: white;
        }
        
        .reject-button {
          background: #f44336;
          color: white;
        }
        
        .cancel-button {
          background: #9e9e9e;
          color: white;
        }
        
        .loading-spinner {
          text-align: center;
          padding: 20px;
          color: #666;
        }
      `}</style>
    </div>
  );
};

export default ExecutionMonitor;
