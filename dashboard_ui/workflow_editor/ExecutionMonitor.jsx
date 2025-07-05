import React, { useState, useEffect, useRef } from 'react';

// --- Helper Components ---

const StatusIcon = ({ status }) => {
  const baseClasses = "w-6 h-6 rounded-full flex items-center justify-center text-white font-bold text-sm flex-shrink-0";
  switch (status) {
    case 'running':
      return (
        <div className={`${baseClasses} bg-blue-500 animate-pulse`}>
          <svg className="w-4 h-4 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        </div>
      );
    case 'completed':
      return <div className={`${baseClasses} bg-green-500`}>✓</div>;
    case 'failed':
      return <div className={`${baseClasses} bg-red-500`}>!</div>;
    case 'pending':
    default:
      return <div className={`${baseClasses} bg-gray-400`}>-</div>;
  }
};

const StepLog = ({ logs }) => {
  if (!logs || logs.length === 0) return null;
  return (
    <div className="mt-2 ml-12 p-3 bg-gray-800 text-gray-200 rounded-md font-mono text-xs max-h-40 overflow-y-auto">
      {logs.map((log, index) => (
        <div key={index} className="whitespace-pre-wrap">{log}</div>
      ))}
    </div>
  );
};

// --- Main Execution Monitor Component ---

const ExecutionMonitor = ({ executionId, workflowName, initialSteps, onClose }) => {
  const [executionDetails, setExecutionDetails] = useState({
    status: 'pending',
    startTime: null,
    endTime: null,
    totalDuration: 0,
  });
  const [steps, setSteps] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const ws = useRef(null);

  useEffect(() => {
    // Initialize steps from props
    if (initialSteps) {
      setSteps(initialSteps.map(step => ({
        ...step,
        status: 'pending',
        logs: [],
        duration: null
      })));
    }

    if (!executionId) return;

    // --- WebSocket Connection ---
    const wsUrl = `wss://your-backend-websocket-url/ws/executions/${executionId}`; // Replace with your actual WebSocket URL
    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      console.log('WebSocket connection established');
      setIsConnected(true);
      setExecutionDetails(prev => ({ ...prev, status: 'running', startTime: new Date() }));
    };

    ws.current.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        handleWsMessage(message);
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    ws.current.onerror = (error) => {
      console.error('WebSocket error:', error);
      setIsConnected(false);
    };

    ws.current.onclose = () => {
      console.log('WebSocket connection closed');
      setIsConnected(false);
      // Finalize status if it hasn't been completed/failed already
      setExecutionDetails(prev => ({
        ...prev,
        status: prev.status === 'running' ? 'completed' : prev.status,
        endTime: prev.endTime || new Date(),
      }));
    };

    // Cleanup on component unmount
    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [executionId, initialSteps]);
  
  // Update total duration whenever end time or start time changes
  useEffect(() => {
      if (executionDetails.startTime && executionDetails.endTime) {
          const duration = (executionDetails.endTime - executionDetails.startTime) / 1000;
          setExecutionDetails(prev => ({...prev, totalDuration: duration.toFixed(2)}));
      }
  }, [executionDetails.startTime, executionDetails.endTime]);

  const handleWsMessage = (message) => {
    const { type, payload } = message;
    
    switch (type) {
      case 'WORKFLOW_STARTED':
        setExecutionDetails({
          status: 'running',
          startTime: new Date(payload.startTime),
          endTime: null,
          totalDuration: 0,
        });
        break;
      case 'STEP_UPDATE':
        setSteps(prevSteps =>
          prevSteps.map(step =>
            step.id === payload.stepId
              ? { ...step, status: payload.status, duration: payload.duration }
              : step
          )
        );
        break;
      case 'STEP_LOG':
        setSteps(prevSteps =>
          prevSteps.map(step =>
            step.id === payload.stepId
              ? { ...step, logs: [...(step.logs || []), payload.log] }
              : step
          )
        );
        break;
      case 'WORKFLOW_COMPLETED':
        setExecutionDetails(prev => ({
          ...prev,
          status: 'completed',
          endTime: new Date(payload.endTime),
        }));
        break;
      case 'WORKFLOW_FAILED':
        setExecutionDetails(prev => ({
          ...prev,
          status: 'failed',
          endTime: new Date(payload.endTime),
        }));
        break;
      default:
        console.warn('Unknown WebSocket message type:', type);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl h-[90vh] flex flex-col">
      {/* Header */}
      <div className="p-4 border-b flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Live Execution: {workflowName}</h2>
          <div className="flex items-center text-sm text-gray-500 mt-1">
            <div className={`w-3 h-3 rounded-full mr-2 ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
            {isConnected ? 'Connected' : 'Disconnected'}
          </div>
        </div>
        <button onClick={onClose} className="text-gray-500 hover:text-gray-800">&times;</button>
      </div>

      {/* Metrics Summary */}
      <div className="p-4 bg-gray-50 grid grid-cols-3 gap-4">
        <div className="text-center">
          <div className="text-sm text-gray-500">Status</div>
          <div className={`text-lg font-bold ${
            executionDetails.status === 'completed' ? 'text-green-600' :
            executionDetails.status === 'failed' ? 'text-red-600' :
            'text-blue-600'
          }`}>{executionDetails.status.toUpperCase()}</div>
        </div>
        <div className="text-center">
          <div className="text-sm text-gray-500">Start Time</div>
          <div className="text-lg font-bold">{executionDetails.startTime ? new Date(executionDetails.startTime).toLocaleTimeString() : 'N/A'}</div>
        </div>
        <div className="text-center">
          <div className="text-sm text-gray-500">Total Duration</div>
          <div className="text-lg font-bold">{executionDetails.totalDuration}s</div>
        </div>
      </div>

      {/* Steps Timeline */}
      <div className="flex-grow p-4 overflow-y-auto">
        <div className="space-y-4">
          {steps.map((step, index) => (
            <div key={step.id} className="p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center">
                <StatusIcon status={step.status} />
                <div className="ml-4 flex-grow">
                  <div className="font-semibold text-gray-700">{step.data.label}</div>
                  <div className="text-xs text-gray-500">Step {index + 1} / {steps.length}</div>
                </div>
                <div className="text-sm text-gray-500">
                  {step.duration ? `${step.duration.toFixed(2)}s` : ''}
                </div>
              </div>
              <StepLog logs={step.logs} />
            </div>
          ))}
        </div>
      </div>
      
      {/* Footer Actions */}
      <div className="p-4 border-t bg-gray-50 flex justify-end space-x-2">
          <button className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50">View Full Log</button>
          {executionDetails.status === 'failed' && (
              <button className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700">Retry Failed Steps</button>
          )}
          {executionDetails.status === 'running' && (
              <button className="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-md hover:bg-red-700">Cancel Execution</button>
          )}
      </div>
    </div>
  );
};

export default ExecutionMonitor;
