import React, { useState, useCallback, useRef, useEffect } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  Panel
} from 'reactflow';
import 'reactflow/dist/style.css';
import './workflow-editor.css';

// Import our custom node components
import { StepBox } from './StepBox';
import { ApprovalBox } from './ApprovalBox';
import { DecisionBox } from './DecisionBox';
import { TriggerBox } from './TriggerBox';
import { ScenarioBox } from './ScenarioBox';
import { FlowConnector } from './FlowConnector';

// Import new components
import PredefinedActionsPanel from './PredefinedActionsPanel';
import NodePropertiesPanel from './NodePropertiesPanel';
import ExecutionMonitor from './ExecutionMonitor';

// Import API endpoints and config
import { ENDPOINTS } from '../config';

// Define custom node types
const nodeTypes = {
  step: StepBox,
  approval: ApprovalBox,
  decision: DecisionBox,
  trigger: TriggerBox,
  scenario: ScenarioBox,
  http: StepBox,
  shell: StepBox,
  llm: StepBox,
};

// Define custom edge types
const edgeTypes = {
  flowConnector: FlowConnector,
};

const WorkflowEditor = ({ taskId, initialData = null }) => {
  const reactFlowWrapper = useRef(null);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [reactFlowInstance, setReactFlowInstance] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [workflowName, setWorkflowName] = useState('New Workflow');
  const [workflowId, setWorkflowId] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [saveSuccess, setSaveSuccess] = useState(false);
  
  // Execution monitoring state
  const [showExecutionMonitor, setShowExecutionMonitor] = useState(false);
  const [executionId, setExecutionId] = useState(null);
  const [executionError, setExecutionError] = useState(null);

  // Load initial workflow data if available
  useEffect(() => {
    if (initialData) {
      setNodes(initialData.nodes || []);
      setEdges(initialData.edges || []);
      if (initialData.name) {
        setWorkflowName(initialData.name);
      }
      if (initialData.id) {
        setWorkflowId(initialData.id);
      }
    } else if (taskId) {
      // If we have a taskId but no initialData, try to load from the task clusters
      const loadTaskClusters = async () => {
        try {
          const response = await fetch(ENDPOINTS.TASK_CLUSTERS(taskId));
          if (!response.ok) throw new Error('Failed to fetch clusters');
          const data = await response.json();
          
          // Convert clusters to workflow nodes and edges
          const workflowNodes = data.nodes.map((node, index) => ({
            id: node.id,
            type: 'step',
            position: { x: 100 + (index % 3) * 200, y: 100 + Math.floor(index / 3) * 100 },
            data: { label: node.label || `Step ${index + 1}` }
          }));
          
          const workflowEdges = data.links.map((link, index) => ({
            id: `e-${index}`,
            source: link.source,
            target: link.target,
            type: 'flowConnector'
          }));
          
          setNodes(workflowNodes);
          setEdges(workflowEdges);
        } catch (err) {
          console.error('Error loading task clusters:', err);
        }
      };
      
      loadTaskClusters();
    }
  }, [initialData, taskId]);

  // Handle connections between nodes
  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge({ ...params, type: 'flowConnector' }, eds)),
    [setEdges]
  );

  // Handle drag over for new node creation
  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  // Handle drop for new node creation
  const onDrop = useCallback(
    (event) => {
      event.preventDefault();

      const reactFlowBounds = reactFlowWrapper.current.getBoundingClientRect();
      const type = event.dataTransfer.getData('application/reactflow');
      
      // Check if the dropped element is valid
      if (typeof type === 'undefined' || !type) {
        return;
      }

      // Get position from drop coordinates
      const position = reactFlowInstance.project({
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top,
      });
      
      // Check if we have predefined action data
      let nodeData = { 
        label: `${type.charAt(0).toUpperCase() + type.slice(1)}`,
      };
      
      try {
        const actionJson = event.dataTransfer.getData('application/json');
        if (actionJson) {
          const action = JSON.parse(actionJson);
          nodeData = {
            ...nodeData,
            label: action.name || nodeData.label,
            ...action.params
          };
        }
      } catch (err) {
        console.error('Error parsing action data:', err);
      }
      
      // Add type-specific default data
      if (type === 'approval') {
        nodeData.requiresApproval = true;
      } else if (type === 'decision') {
        nodeData.conditions = [];
      } else if (type === 'trigger') {
        nodeData.triggerType = 'manual';
      }
      
      // Create a new node
      const newNode = {
        id: `${type}-${Date.now()}`,
        type,
        position,
        data: nodeData,
      };

      setNodes((nds) => nds.concat(newNode));
    },
    [reactFlowInstance, setNodes]
  );

  // Handle node selection
  const onNodeClick = useCallback((_, node) => {
    setSelectedNode(node);
  }, []);

  // Handle node update
  const onNodeUpdate = useCallback((nodeId, newData) => {
    setNodes((nds) =>
      nds.map((node) => {
        if (node.id === nodeId) {
          return { ...node, data: { ...node.data, ...newData } };
        }
        return node;
      })
    );
  }, [setNodes]);

  // Handle workflow save
  const saveWorkflow = async () => {
    if (!workflowName.trim()) {
      setSaveError('Please provide a workflow name');
      return;
    }

    setIsSaving(true);
    setSaveError(null);
    setSaveSuccess(false);

    try {
      const workflowData = {
        name: workflowName,
        description: `Workflow created from task ${taskId}`,
        status: "draft",
        created_by: "user",
        task_id: taskId,
        nodes: nodes,
        edges: edges
      };

      // If we have a workflow ID, update instead of create
      const url = workflowId 
        ? `${ENDPOINTS.WORKFLOWS}/${workflowId}`
        : ENDPOINTS.WORKFLOWS;
      
      const method = workflowId ? 'PUT' : 'POST';

      const response = await fetch(url, {
        method: method,
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(workflowData),
      });

      if (!response.ok) {
        throw new Error(`Failed to save workflow: ${response.statusText}`);
      }

      const result = await response.json();
      setSaveSuccess(true);
      
      // If this was a new workflow, store the ID
      if (!workflowId && result.id) {
        setWorkflowId(result.id);
      }
      
      console.log('Workflow saved:', result);
    } catch (error) {
      console.error('Error saving workflow:', error);
      setSaveError(error.message);
    } finally {
      setIsSaving(false);
    }
  };
  
  // Handle workflow execution
  const executeWorkflow = async () => {
    // Must save first if no workflow ID
    if (!workflowId) {
      setSaveError('Please save the workflow before executing');
      return;
    }
    
    setIsExecuting(true);
    setExecutionError(null);
    
    try {
      const response = await fetch(`${ENDPOINTS.WORKFLOW_BY_ID(workflowId)}/trigger`, {
        method: 'POST',
      });
      
      if (!response.ok) {
        throw new Error(`Failed to trigger workflow: ${response.statusText}`);
      }
      
      const result = await response.json();
      console.log('Workflow triggered:', result);
      
      // If we have an execution ID, show the monitor
      if (result.execution_id) {
        setExecutionId(result.execution_id);
        setShowExecutionMonitor(true);
      }
    } catch (error) {
      console.error('Error executing workflow:', error);
      setExecutionError(error.message);
    } finally {
      setIsExecuting(false);
    }
  };

  // Handle predefined action selection
  const handleActionSelect = (action) => {
    // Create a node from the selected action
    if (!reactFlowInstance) return;
    
    // Create node in the center of the visible area
    const centerX = reactFlowInstance.getViewport().x + reactFlowInstance.getViewport().width / 2;
    const centerY = reactFlowInstance.getViewport().y + reactFlowInstance.getViewport().height / 2;
    
    const newNode = {
      id: `${action.type}-${Date.now()}`,
      type: action.type,
      position: { x: centerX, y: centerY },
      data: {
        label: action.name || action.type,
        ...action.params
      },
    };
    
    setNodes((nds) => nds.concat(newNode));
  };
  
  // Close execution monitor
  const closeExecutionMonitor = () => {
    setShowExecutionMonitor(false);
  };

  return (
    <div className="workflow-editor-container">
      <ReactFlowProvider>
        <div className="reactflow-wrapper" ref={reactFlowWrapper}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onInit={setReactFlowInstance}
            onDrop={onDrop}
            onDragOver={onDragOver}
            onNodeClick={onNodeClick}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            fitView
          >
            <Controls />
            <Background variant="dots" gap={12} size={1} />
            
            {/* Toolbar */}
            <Panel position="top-left" className="workflow-toolbar">
              <div className="toolbar-header">
                <input
                  type="text"
                  value={workflowName}
                  onChange={(e) => setWorkflowName(e.target.value)}
                  placeholder="Workflow Name"
                  className="workflow-name-input"
                />
                <div className="button-group">
                  <button 
                    onClick={saveWorkflow} 
                    className="save-button"
                    disabled={isSaving}
                  >
                    {isSaving ? 'Saving...' : 'Save Workflow'}
                  </button>
                  <button 
                    onClick={executeWorkflow} 
                    className="execute-button"
                    disabled={isExecuting || !workflowId}
                  >
                    {isExecuting ? 'Executing...' : 'Execute'}
                  </button>
                </div>
              </div>
              
              {saveError && <div className="error-message">{saveError}</div>}
              {saveSuccess && <div className="success-message">Workflow saved successfully!</div>}
              {executionError && <div className="error-message">{executionError}</div>}
              
              {/* Replace node palette with PredefinedActionsPanel */}
              <PredefinedActionsPanel onActionSelect={handleActionSelect} />
            </Panel>
            
            {/* Replace with new NodePropertiesPanel */}
            {selectedNode && (
              <Panel position="top-right">
                <NodePropertiesPanel 
                  selectedNode={selectedNode}
                  onUpdate={onNodeUpdate}
                  onClose={() => setSelectedNode(null)}
                />
              </Panel>
            )}
            
            {/* Execution Monitor (conditionally rendered) */}
            {showExecutionMonitor && executionId && (
              <div className="execution-monitor-overlay">
                <ExecutionMonitor 
                  executionId={executionId}
                  workflowId={workflowId}
                  onClose={closeExecutionMonitor}
                />
              </div>
            )}
          </ReactFlow>
        </div>
      </ReactFlowProvider>
      
      <style jsx>{`
        .button-group {
          display: flex;
          gap: 8px;
        }
        
        .execute-button {
          padding: 8px 16px;
          background: #4caf50;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-weight: 500;
        }
        
        .execute-button:hover {
          background: #388e3c;
        }
        
        .execute-button:disabled {
          background: #ccc;
          cursor: not-allowed;
        }
        
        .execution-monitor-overlay {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.5);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 10;
        }
      `}</style>
    </div>
  );
};

export default WorkflowEditor;
