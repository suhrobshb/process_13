import React, { useState, useEffect } from 'react';
import { ENDPOINTS } from '../config';

/**
 * PredefinedActionsPanel Component
 * ---------------------------------
 * Displays a panel of predefined actions that can be dragged onto the workflow editor.
 * Actions are fetched from the backend API and can be filtered by category.
 * 
 * Props:
 * - onActionSelect: Optional callback when an action is selected (not dragged)
 * - className: Optional additional CSS classes
 */
const PredefinedActionsPanel = ({ onActionSelect, className = '' }) => {
  // State for categories, actions, and UI state
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [actions, setActions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch categories on mount
  useEffect(() => {
    const fetchCategories = async () => {
      try {
        setIsLoading(true);
        const response = await fetch(ENDPOINTS.LIBRARY_CATEGORIES);
        
        if (!response.ok) {
          throw new Error(`Failed to fetch categories: ${response.statusText}`);
        }
        
        const data = await response.json();
        setCategories(data);
        
        // Auto-select first category if available
        if (data.length > 0) {
          setSelectedCategory(data[0].id);
        }
      } catch (err) {
        console.error('Error fetching action categories:', err);
        setError('Failed to load action categories. Please try again later.');
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchCategories();
  }, []);

  // Fetch actions when selected category changes
  useEffect(() => {
    const fetchActions = async () => {
      if (!selectedCategory) return;
      
      try {
        setIsLoading(true);
        const response = await fetch(`${ENDPOINTS.LIBRARY_CATEGORIES}/${selectedCategory}`);
        
        if (!response.ok) {
          throw new Error(`Failed to fetch actions: ${response.statusText}`);
        }
        
        const data = await response.json();
        setActions(data.actions || []);
      } catch (err) {
        console.error(`Error fetching actions for category ${selectedCategory}:`, err);
        setError('Failed to load actions. Please try again later.');
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchActions();
  }, [selectedCategory]);

  // Handle drag start to set data for the workflow editor
  const handleDragStart = (event, action) => {
    // Set the data transfer properties for the drag operation
    event.dataTransfer.setData('application/reactflow', action.type);
    event.dataTransfer.setData('application/json', JSON.stringify(action));
    event.dataTransfer.effectAllowed = 'move';
  };

  // Handle category change
  const handleCategoryChange = (e) => {
    setSelectedCategory(e.target.value);
  };

  // Handle action click (optional selection)
  const handleActionClick = (action) => {
    if (onActionSelect) {
      onActionSelect(action);
    }
  };

  return (
    <div className={`predefined-actions-panel ${className}`}>
      <h3 className="panel-title">Predefined Actions</h3>
      
      {/* Category selector */}
      <div className="category-selector">
        <label htmlFor="category-select">Category:</label>
        <select 
          id="category-select" 
          value={selectedCategory || ''} 
          onChange={handleCategoryChange}
          disabled={isLoading || categories.length === 0}
        >
          {categories.map(category => (
            <option key={category.id} value={category.id}>
              {category.title}
            </option>
          ))}
        </select>
      </div>
      
      {/* Error message */}
      {error && (
        <div className="error-message">
          {error}
        </div>
      )}
      
      {/* Loading indicator */}
      {isLoading && (
        <div className="loading-indicator">
          Loading...
        </div>
      )}
      
      {/* Actions list */}
      <div className="actions-list">
        {!isLoading && actions.map(action => (
          <div
            key={action.id}
            className={`action-item ${action.type}-action`}
            draggable
            onDragStart={(e) => handleDragStart(e, action)}
            onClick={() => handleActionClick(action)}
          >
            <div className="action-header">
              <span className="action-name">{action.name}</span>
              <span className="action-type">{action.type}</span>
            </div>
            <div className="action-description">
              {action.description}
            </div>
          </div>
        ))}
        
        {!isLoading && actions.length === 0 && !error && (
          <div className="no-actions-message">
            No actions available in this category.
          </div>
        )}
      </div>
      
      <style jsx>{`
        .predefined-actions-panel {
          background: white;
          border-radius: 6px;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
          padding: 16px;
          max-height: 100%;
          overflow-y: auto;
        }
        
        .panel-title {
          margin-top: 0;
          margin-bottom: 16px;
          font-size: 16px;
          font-weight: 600;
          color: #333;
          border-bottom: 1px solid #eee;
          padding-bottom: 8px;
        }
        
        .category-selector {
          margin-bottom: 16px;
        }
        
        .category-selector select {
          width: 100%;
          padding: 8px;
          border: 1px solid #ddd;
          border-radius: 4px;
          margin-top: 4px;
        }
        
        .actions-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        
        .action-item {
          padding: 12px;
          border-radius: 4px;
          cursor: grab;
          user-select: none;
          transition: transform 0.1s, box-shadow 0.1s;
        }
        
        .action-item:hover {
          transform: translateY(-2px);
          box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
        }
        
        .action-item:active {
          cursor: grabbing;
        }
        
        .action-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 4px;
        }
        
        .action-name {
          font-weight: 500;
        }
        
        .action-type {
          font-size: 12px;
          padding: 2px 6px;
          border-radius: 10px;
          background: #f1f3f4;
        }
        
        .action-description {
          font-size: 13px;
          color: #555;
        }
        
        .error-message {
          color: #d32f2f;
          padding: 8px;
          background: #ffebee;
          border-radius: 4px;
          margin-bottom: 16px;
        }
        
        .loading-indicator {
          text-align: center;
          padding: 16px;
          color: #666;
        }
        
        .no-actions-message {
          text-align: center;
          padding: 16px;
          color: #666;
        }
        
        /* Action type specific styling */
        .http-action {
          background: #e3f2fd;
          border: 1px solid #90caf9;
        }
        
        .shell-action {
          background: #e8f5e9;
          border: 1px solid #a5d6a7;
        }
        
        .llm-action {
          background: #f3e5f5;
          border: 1px solid #ce93d8;
        }
        
        .decision-action {
          background: #fff8e1;
          border: 1px solid #ffecb3;
        }
        
        .approval-action {
          background: #fbe9e7;
          border: 1px solid #ffccbc;
        }
      `}</style>
    </div>
  );
};

export default PredefinedActionsPanel;
