import React, { useState, useEffect, useCallback, useRef } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  MiniMap,
} from 'reactflow';
import 'reactflow/dist/style.css';

// --- Custom Node Component for Action Step Boxes ---

const ActionStepNode = ({ data }) => {
  const confidence = data.confidence_score || 0;
  let confidenceColor = 'bg-green-500';
  if (confidence < 0.9) confidenceColor = 'bg-yellow-500';
  if (confidence < 0.7) confidenceColor = 'bg-red-500';

  let statusOverlay = null;
  if (data.status) {
    let statusColor = '';
    let statusText = '';
    switch (data.status) {
      case 'running':
        statusColor = 'bg-blue-500/80';
        statusText = 'Running...';
        break;
      case 'completed':
        statusColor = 'bg-green-500/80';
        statusText = '✅ Completed';
        break;
      case 'failed':
        statusColor = 'bg-red-500/80';
        statusText = '❌ Failed';
        break;
    }
    statusOverlay = (
      <div className={`absolute inset-0 ${statusColor} flex items-center justify-center text-white font-bold text-lg rounded-md`}>
        {statusText}
      </div>
    );
  }

  return (
    <div className="p-4 border rounded-lg bg-white shadow-md w-80 relative">
      <div className="font-bold text-lg mb-2">{data.label}</div>
      <p className="text-sm text-gray-600 mb-4">{data.description}</p>
      <div className="text-xs text-gray-400">AI Confidence</div>
      <div className="w-full bg-gray-200 rounded-full h-2.5">
        <div
          className={`${confidenceColor} h-2.5 rounded-full`}
          style={{ width: `${confidence * 100}%` }}
        ></div>
      </div>
      <div className="text-right text-xs font-bold mt-1">{`${Math.round(confidence * 100)}%`}</div>
      {statusOverlay}
    </div>
  );
};

const nodeTypes = { actionStep: ActionStepNode };

// --- Main Workflow Editor Component ---

const WorkflowEditor = ({ structuredWorkflow, onSave, onRun }) => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [executionLogs, setExecutionLogs] = useState([]);
  const [isExecuting, setIsExecuting] = useState(false);

  // Load workflow data when the component receives it
  useEffect(() => {
    if (structuredWorkflow && structuredWorkflow.nodes) {
      const initialNodes = structuredWorkflow.nodes.map((node, index) => ({
        id: node.id,
        type: 'actionStep',
        position: { x: 250, y: index * 200 },
        data: {
          label: node.data.label,
          description: node.data.description,
          confidence_score: node.data.confidence_score,
          raw_actions: node.data.raw_actions,
          status: null, // Initial status
        },
      }));
      const initialEdges = structuredWorkflow.edges.map(edge => ({
        ...edge,
        animated: false,
        style: { stroke: '#6b7280', strokeWidth: 2 },
      }));
      setNodes(initialNodes);
      setEdges(initialEdges);
      setExecutionLogs([]);
      setIsExecuting(false);
    }
  }, [structuredWorkflow]);

  const onNodeClick = useCallback((event, node) => {
    setSelectedNode(node);
  }, []);

  const handlePaneClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  const updateNodeData = (nodeId, newData) => {
    setNodes((nds) =>
      nds.map((node) => {
        if (node.id === nodeId) {
          return {
            ...node,
            data: { ...node.data, ...newData },
          };
        }
        return node;
      })
    );
  };
  
  // --- Live Execution Simulation ---
  const handleRunWorkflow = () => {
    if (!onRun) {
        console.warn("onRun handler not provided to WorkflowEditor");
        return;
    }
    
    setIsExecuting(true);
    setExecutionLogs(['Workflow execution started...']);
    
    // Reset node statuses
    setNodes(nds => nds.map(n => ({ ...n, data: { ...n.data, status: 'pending' } })));
    
    const executionOrder = structuredWorkflow.nodes.map(n => n.id);
    let currentStep = 0;

    const runNextStep = () => {
      if (currentStep >= executionOrder.length) {
        setExecutionLogs(logs => [...logs, 'Workflow execution finished.']);
        setIsExecuting(false);
        return;
      }

      const nodeId = executionOrder[currentStep];
      
      // Mark current step as running
      setNodes(nds => nds.map(n => n.id === nodeId ? { ...n, data: { ...n.data, status: 'running' } } : n));
      setExecutionLogs(logs => [...logs, `Executing step: ${nodes.find(n => n.id === nodeId)?.data.label}`]);

      // Simulate step execution
      setTimeout(() => {
        const success = Math.random() > 0.1; // 90% success rate
        const newStatus = success ? 'completed' : 'failed';
        
        setNodes(nds => nds.map(n => n.id === nodeId ? { ...n, data: { ...n.data, status: newStatus } } : n));
        setExecutionLogs(logs => [...logs, `Step ${success ? 'completed' : 'failed'}: ${nodes.find(n => n.id === nodeId)?.data.label}`]);

        if (success) {
          currentStep++;
          runNextStep();
        } else {
          setExecutionLogs(logs => [...logs, 'Workflow execution halted due to failure.']);
          setIsExecuting(false);
        }
      }, 2000 + Math.random() * 1000); // Simulate 2-3 second execution time
    };

    runNextStep();
    onRun(structuredWorkflow);
  };

  return (
    <div className="flex h-full bg-gray-100">
      <ReactFlowProvider>
        <div className="flex-grow h-full relative">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            onPaneClick={handlePaneClick}
            nodeTypes={nodeTypes}
            fitView
          >
            <Background />
            <Controls />
            <MiniMap />
          </ReactFlow>
          <div className="absolute top-4 left-4 z-10 bg-white p-2 rounded shadow-md">
            <button 
              onClick={handleRunWorkflow} 
              disabled={isExecuting}
              className="bg-green-500 hover:bg-green-600 text-white font-bold py-2 px-4 rounded disabled:bg-gray-400"
            >
              {isExecuting ? 'Executing...' : 'Run Workflow'}
            </button>
          </div>
        </div>
      </ReactFlowProvider>

      {/* Side Panel for Editing and Monitoring */}
      <div className="w-96 bg-white border-l border-gray-200 flex flex-col">
        {selectedNode ? (
          // Properties Editor
          <div className="p-4 flex-grow">
            <h3 className="text-xl font-bold mb-4">Edit Action Step</h3>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700">Title</label>
              <input
                type="text"
                value={selectedNode.data.label}
                onChange={(e) => updateNodeData(selectedNode.id, { label: e.target.value })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">AI-Generated Description</label>
              <textarea
                rows="6"
                value={selectedNode.data.description}
                onChange={(e) => updateNodeData(selectedNode.id, { description: e.target.value })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
              ></textarea>
            </div>
             <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700">Confidence Score</label>
                <p className="text-lg font-semibold">{`${Math.round(selectedNode.data.confidence_score * 100)}%`}</p>
                {selectedNode.data.confidence_score < 0.8 && (
                    <p className="text-sm text-yellow-600">Low confidence. Please review and refine the description for better accuracy.</p>
                )}
            </div>
          </div>
        ) : (
          // Live Execution Monitor
          <div className="p-4 flex-grow flex flex-col">
            <h3 className="text-xl font-bold mb-4">Live Execution Monitor</h3>
            <div className="bg-gray-800 text-white font-mono text-sm rounded-md p-4 flex-grow overflow-y-auto">
              {executionLogs.map((log, index) => (
                <div key={index} className="whitespace-pre-wrap">
                  <span className="text-gray-500 mr-2">{`[${new Date().toLocaleTimeString()}]`}</span>
                  <span>{log}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default WorkflowEditor;
