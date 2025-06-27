import React, { useState, useEffect } from 'react';

/**
 * NodePropertiesPanel Component
 * -----------------------------
 * Displays and allows editing of properties for the selected node in the workflow editor.
 * Different form fields are shown based on the node type.
 * 
 * Props:
 * - selectedNode: The currently selected node object
 * - onUpdate: Function to call when node properties are updated
 * - onClose: Function to call when the panel is closed
 */
const NodePropertiesPanel = ({ selectedNode, onUpdate, onClose }) => {
  const [nodeData, setNodeData] = useState({});
  
  // Initialize form data when selected node changes
  useEffect(() => {
    if (selectedNode && selectedNode.data) {
      setNodeData({ ...selectedNode.data });
    }
  }, [selectedNode]);
  
  if (!selectedNode) return null;
  
  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    const newValue = type === 'checkbox' ? checked : value;
    
    setNodeData(prev => ({
      ...prev,
      [name]: newValue
    }));
  };
  
  const handleNestedChange = (section, field, value) => {
    setNodeData(prev => ({
      ...prev,
      [section]: {
        ...(prev[section] || {}),
        [field]: value
      }
    }));
  };
  
  const handleSubmit = (e) => {
    e.preventDefault();
    onUpdate(selectedNode.id, nodeData);
  };
  
  // Handle array of items (for conditions, approvers, etc.)
  const handleArrayItem = (arrayName, index, value) => {
    const array = [...(nodeData[arrayName] || [])];
    
    if (value === null) {
      // Remove item
      array.splice(index, 1);
    } else if (index === -1) {
      // Add new item
      array.push(value);
    } else {
      // Update existing item
      array[index] = value;
    }
    
    setNodeData(prev => ({
      ...prev,
      [arrayName]: array
    }));
  };
  
  // Add a new condition to decision node
  const addCondition = () => {
    handleArrayItem('conditions', -1, { expression: '', target: '' });
  };
  
  // Add a new approver to approval node
  const addApprover = () => {
    handleArrayItem('approvers', -1, '');
  };
  
  // Common properties for all node types
  const renderCommonProperties = () => (
    <div className="property-group">
      <label htmlFor="label">Label:</label>
      <input
        type="text"
        id="label"
        name="label"
        value={nodeData.label || ''}
        onChange={handleChange}
        placeholder="Node Label"
      />
    </div>
  );
  
  // HTTP node specific properties
  const renderHttpProperties = () => (
    <>
      <div className="property-group">
        <label htmlFor="url">URL:</label>
        <input
          type="text"
          id="url"
          name="url"
          value={nodeData.url || ''}
          onChange={handleChange}
          placeholder="https://api.example.com/endpoint"
        />
      </div>
      
      <div className="property-group">
        <label htmlFor="method">Method:</label>
        <select
          id="method"
          name="method"
          value={nodeData.method || 'GET'}
          onChange={handleChange}
        >
          <option value="GET">GET</option>
          <option value="POST">POST</option>
          <option value="PUT">PUT</option>
          <option value="DELETE">DELETE</option>
          <option value="PATCH">PATCH</option>
        </select>
      </div>
      
      <div className="property-group">
        <label htmlFor="headers">Headers (JSON):</label>
        <textarea
          id="headers"
          name="headers"
          value={nodeData.headers ? JSON.stringify(nodeData.headers, null, 2) : ''}
          onChange={(e) => {
            try {
              const headers = e.target.value ? JSON.parse(e.target.value) : {};
              setNodeData(prev => ({ ...prev, headers }));
            } catch (err) {
              // Don't update if JSON is invalid
            }
          }}
          placeholder='{"Content-Type": "application/json"}'
          rows={4}
        />
      </div>
      
      <div className="property-group">
        <label htmlFor="body">Request Body (JSON):</label>
        <textarea
          id="body"
          name="body"
          value={nodeData.body ? JSON.stringify(nodeData.body, null, 2) : ''}
          onChange={(e) => {
            try {
              const body = e.target.value ? JSON.parse(e.target.value) : {};
              setNodeData(prev => ({ ...prev, body }));
            } catch (err) {
              // Don't update if JSON is invalid
            }
          }}
          placeholder='{"key": "value"}'
          rows={4}
        />
      </div>
      
      <div className="property-group">
        <label htmlFor="timeout">Timeout (seconds):</label>
        <input
          type="number"
          id="timeout"
          name="timeout"
          value={nodeData.timeout || 30}
          onChange={handleChange}
          min={1}
          max={300}
        />
      </div>
    </>
  );
  
  // Shell node specific properties
  const renderShellProperties = () => (
    <>
      <div className="property-group">
        <label htmlFor="command">Command:</label>
        <textarea
          id="command"
          name="command"
          value={nodeData.command || ''}
          onChange={handleChange}
          placeholder="ls -la ${directory}"
          rows={3}
        />
      </div>
      
      <div className="property-group">
        <label htmlFor="timeout">Timeout (seconds):</label>
        <input
          type="number"
          id="timeout"
          name="timeout"
          value={nodeData.timeout || 60}
          onChange={handleChange}
          min={1}
          max={3600}
        />
      </div>
      
      <div className="property-group">
        <label>
          <input
            type="checkbox"
            name="shell"
            checked={nodeData.shell !== false}
            onChange={handleChange}
          />
          Use shell
        </label>
      </div>
      
      <div className="property-group">
        <label htmlFor="env">Environment Variables (JSON):</label>
        <textarea
          id="env"
          name="env"
          value={nodeData.env ? JSON.stringify(nodeData.env, null, 2) : ''}
          onChange={(e) => {
            try {
              const env = e.target.value ? JSON.parse(e.target.value) : {};
              setNodeData(prev => ({ ...prev, env }));
            } catch (err) {
              // Don't update if JSON is invalid
            }
          }}
          placeholder='{"VAR1": "value1", "VAR2": "value2"}'
          rows={4}
        />
      </div>
    </>
  );
  
  // LLM node specific properties
  const renderLlmProperties = () => (
    <>
      <div className="property-group">
        <label htmlFor="provider">Provider:</label>
        <select
          id="provider"
          name="provider"
          value={nodeData.provider || 'openai'}
          onChange={handleChange}
        >
          <option value="openai">OpenAI</option>
          <option value="anthropic">Anthropic</option>
          <option value="local">Local Model</option>
        </select>
      </div>
      
      <div className="property-group">
        <label htmlFor="model">Model:</label>
        <input
          type="text"
          id="model"
          name="model"
          value={nodeData.model || ''}
          onChange={handleChange}
          placeholder="gpt-4"
        />
      </div>
      
      <div className="property-group">
        <label htmlFor="prompt">Prompt:</label>
        <textarea
          id="prompt"
          name="prompt"
          value={nodeData.prompt || ''}
          onChange={handleChange}
          placeholder="Enter your prompt here. You can use ${variables} for substitution."
          rows={6}
        />
      </div>
      
      <div className="property-group">
        <label htmlFor="temperature">Temperature:</label>
        <input
          type="number"
          id="temperature"
          name="temperature"
          value={nodeData.temperature || 0.7}
          onChange={handleChange}
          min={0}
          max={2}
          step={0.1}
        />
      </div>
      
      <div className="property-group">
        <label htmlFor="maxTokens">Max Tokens:</label>
        <input
          type="number"
          id="maxTokens"
          name="maxTokens"
          value={nodeData.maxTokens || 1000}
          onChange={handleChange}
          min={1}
          max={8192}
        />
      </div>
    </>
  );
  
  // Decision node specific properties
  const renderDecisionProperties = () => (
    <>
      <div className="property-group">
        <label htmlFor="conditions">Conditions:</label>
        <div className="conditions-list">
          {(nodeData.conditions || []).map((condition, index) => (
            <div key={index} className="condition-item">
              <div className="condition-row">
                <input
                  type="text"
                  value={condition.expression || ''}
                  onChange={(e) => {
                    const updatedCondition = { ...condition, expression: e.target.value };
                    handleArrayItem('conditions', index, updatedCondition);
                  }}
                  placeholder="Expression (e.g., ${value} > 10)"
                />
                <button
                  type="button"
                  onClick={() => handleArrayItem('conditions', index, null)}
                  className="remove-button"
                >
                  ✕
                </button>
              </div>
              <div className="condition-row">
                <input
                  type="text"
                  value={condition.target || ''}
                  onChange={(e) => {
                    const updatedCondition = { ...condition, target: e.target.value };
                    handleArrayItem('conditions', index, updatedCondition);
                  }}
                  placeholder="Target node ID"
                />
              </div>
            </div>
          ))}
        </div>
        <button type="button" onClick={addCondition} className="add-button">
          Add Condition
        </button>
      </div>
      
      <div className="property-group">
        <label htmlFor="default">Default Target:</label>
        <input
          type="text"
          id="default"
          name="default"
          value={nodeData.default || ''}
          onChange={handleChange}
          placeholder="Default target node ID"
        />
      </div>
    </>
  );
  
  // Approval node specific properties
  const renderApprovalProperties = () => (
    <>
      <div className="property-group">
        <label htmlFor="title">Approval Title:</label>
        <input
          type="text"
          id="title"
          name="title"
          value={nodeData.title || ''}
          onChange={handleChange}
          placeholder="Approval Request Title"
        />
      </div>
      
      <div className="property-group">
        <label htmlFor="description">Description:</label>
        <textarea
          id="description"
          name="description"
          value={nodeData.description || ''}
          onChange={handleChange}
          placeholder="Describe what needs to be approved"
          rows={4}
        />
      </div>
      
      <div className="property-group">
        <label htmlFor="approvers">Approvers:</label>
        <div className="approvers-list">
          {(nodeData.approvers || []).map((approver, index) => (
            <div key={index} className="approver-item">
              <input
                type="text"
                value={approver || ''}
                onChange={(e) => handleArrayItem('approvers', index, e.target.value)}
                placeholder="Email address"
              />
              <button
                type="button"
                onClick={() => handleArrayItem('approvers', index, null)}
                className="remove-button"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
        <button type="button" onClick={addApprover} className="add-button">
          Add Approver
        </button>
      </div>
      
      <div className="property-group">
        <label htmlFor="timeoutHours">Timeout (hours):</label>
        <input
          type="number"
          id="timeoutHours"
          name="timeoutHours"
          value={nodeData.timeoutHours || 24}
          onChange={handleChange}
          min={1}
          max={168}
        />
      </div>
      
      <div className="property-group">
        <label htmlFor="notificationMethod">Notification Method:</label>
        <select
          id="notificationMethod"
          name="notificationMethod"
          value={nodeData.notificationMethod || 'email'}
          onChange={handleChange}
        >
          <option value="email">Email</option>
          <option value="slack">Slack</option>
          <option value="both">Both</option>
        </select>
      </div>
      
      <div className="property-group">
        <label>
          <input
            type="checkbox"
            name="wait"
            checked={nodeData.wait !== false}
            onChange={handleChange}
          />
          Wait for approval before continuing
        </label>
      </div>
    </>
  );
  
  // Render properties based on node type
  const renderTypeSpecificProperties = () => {
    const nodeType = selectedNode.type || 'step';
    
    switch (nodeType) {
      case 'http':
        return renderHttpProperties();
      case 'shell':
        return renderShellProperties();
      case 'llm':
        return renderLlmProperties();
      case 'decision':
        return renderDecisionProperties();
      case 'approval':
        return renderApprovalProperties();
      default:
        return null;
    }
  };
  
  return (
    <div className="node-properties-panel">
      <div className="panel-header">
        <h3>Node Properties: {selectedNode.type}</h3>
        <button type="button" onClick={onClose} className="close-button">
          ✕
        </button>
      </div>
      
      <form onSubmit={handleSubmit}>
        {renderCommonProperties()}
        {renderTypeSpecificProperties()}
        
        <div className="button-group">
          <button type="submit" className="save-button">
            Apply Changes
          </button>
        </div>
      </form>
      
      <style jsx>{`
        .node-properties-panel {
          background: white;
          padding: 16px;
          border-radius: 6px;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
          width: 300px;
          max-height: calc(100% - 40px);
          overflow-y: auto;
        }
        
        .panel-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
          border-bottom: 1px solid #eee;
          padding-bottom: 8px;
        }
        
        .panel-header h3 {
          margin: 0;
          font-size: 16px;
          font-weight: 600;
          color: #333;
        }
        
        .close-button {
          background: none;
          border: none;
          cursor: pointer;
          font-size: 16px;
          color: #666;
        }
        
        .property-group {
          margin-bottom: 16px;
        }
        
        .property-group label {
          display: block;
          margin-bottom: 6px;
          font-weight: 500;
          font-size: 14px;
          color: #555;
        }
        
        .property-group input[type="text"],
        .property-group input[type="number"],
        .property-group select,
        .property-group textarea {
          width: 100%;
          padding: 8px 10px;
          border: 1px solid #ddd;
          border-radius: 4px;
          font-size: 14px;
          transition: border-color 0.2s;
        }
        
        .property-group input[type="text"]:focus,
        .property-group input[type="number"]:focus,
        .property-group select:focus,
        .property-group textarea:focus {
          outline: none;
          border-color: #4285F4;
          box-shadow: 0 0 0 2px rgba(66, 133, 244, 0.2);
        }
        
        .property-group input[type="checkbox"] {
          margin-right: 6px;
        }
        
        .conditions-list,
        .approvers-list {
          margin-bottom: 8px;
        }
        
        .condition-item,
        .approver-item {
          margin-bottom: 8px;
          padding: 8px;
          background: #f5f5f5;
          border-radius: 4px;
        }
        
        .condition-row {
          display: flex;
          gap: 8px;
          margin-bottom: 8px;
        }
        
        .condition-row:last-child {
          margin-bottom: 0;
        }
        
        .approver-item {
          display: flex;
          gap: 8px;
        }
        
        .remove-button {
          background: #f44336;
          color: white;
          border: none;
          border-radius: 4px;
          width: 24px;
          height: 24px;
          font-size: 12px;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }
        
        .add-button {
          background: #4caf50;
          color: white;
          border: none;
          border-radius: 4px;
          padding: 6px 12px;
          cursor: pointer;
          font-size: 14px;
        }
        
        .button-group {
          display: flex;
          justify-content: flex-end;
          margin-top: 20px;
        }
        
        .save-button {
          padding: 8px 16px;
          background: #4285F4;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-weight: 500;
        }
        
        .save-button:hover {
          background: #3367d6;
        }
      `}</style>
    </div>
  );
};

export default NodePropertiesPanel;
