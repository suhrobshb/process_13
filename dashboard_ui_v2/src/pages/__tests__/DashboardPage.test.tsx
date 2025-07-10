/**
 * Dashboard Page Tests
 * ===================
 */

import React from 'react';
import { render, screen, waitFor } from '../../test-utils';
import { DashboardPage } from '../DashboardPage';

// Mock the API calls
jest.mock('../../lib/api', () => ({
  getWorkflows: jest.fn(() => Promise.resolve({
    data: [
      {
        id: '1',
        name: 'Test Workflow 1',
        status: 'active',
        created_at: '2023-01-01T00:00:00Z'
      },
      {
        id: '2', 
        name: 'Test Workflow 2',
        status: 'paused',
        created_at: '2023-01-02T00:00:00Z'
      }
    ]
  })),
  getExecutions: jest.fn(() => Promise.resolve({
    data: [
      {
        id: '1',
        workflow_id: '1',
        status: 'completed',
        started_at: '2023-01-01T10:00:00Z'
      }
    ]
  })),
  getDashboardStats: jest.fn(() => Promise.resolve({
    data: {
      total_workflows: 15,
      active_workflows: 8,
      total_executions: 142,
      successful_executions: 128
    }
  }))
}));

describe('DashboardPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders dashboard page elements', async () => {
    render(<DashboardPage />);
    
    // Check for main heading
    expect(screen.getByText(/dashboard/i)).toBeInTheDocument();
    
    // Check for stats cards loading states initially
    expect(screen.getByText(/loading.../i)).toBeInTheDocument();
  });

  it('displays dashboard statistics', async () => {
    render(<DashboardPage />);
    
    // Wait for stats to load
    await waitFor(() => {
      expect(screen.getByText('15')).toBeInTheDocument(); // total workflows
      expect(screen.getByText('8')).toBeInTheDocument();  // active workflows
      expect(screen.getByText('142')).toBeInTheDocument(); // total executions
    });
  });

  it('displays recent workflows section', async () => {
    render(<DashboardPage />);
    
    await waitFor(() => {
      expect(screen.getByText(/recent workflows/i)).toBeInTheDocument();
      expect(screen.getByText('Test Workflow 1')).toBeInTheDocument();
      expect(screen.getByText('Test Workflow 2')).toBeInTheDocument();
    });
  });

  it('displays workflow status badges', async () => {
    render(<DashboardPage />);
    
    await waitFor(() => {
      expect(screen.getByText('active')).toBeInTheDocument();
      expect(screen.getByText('paused')).toBeInTheDocument();
    });
  });

  it('displays recent executions section', async () => {
    render(<DashboardPage />);
    
    await waitFor(() => {
      expect(screen.getByText(/recent executions/i)).toBeInTheDocument();
      expect(screen.getByText('completed')).toBeInTheDocument();
    });
  });

  it('handles loading states properly', () => {
    render(<DashboardPage />);
    
    // Should show loading indicators
    expect(screen.getAllByText(/loading/i)).toHaveLength(3); // stats, workflows, executions
  });

  it('renders create workflow button', async () => {
    render(<DashboardPage />);
    
    const createButton = screen.getByRole('button', { name: /create workflow/i });
    expect(createButton).toBeInTheDocument();
  });

  it('renders view all workflows link', async () => {
    render(<DashboardPage />);
    
    await waitFor(() => {
      const viewAllLink = screen.getByText(/view all workflows/i);
      expect(viewAllLink).toBeInTheDocument();
    });
  });

  it('handles API errors gracefully', async () => {
    // Mock API to return error
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
    
    require('../../lib/api').getWorkflows.mockRejectedValueOnce(
      new Error('API Error')
    );
    
    render(<DashboardPage />);
    
    await waitFor(() => {
      expect(screen.getByText(/error loading data/i)).toBeInTheDocument();
    });
    
    consoleSpy.mockRestore();
  });

  it('refreshes data when refresh button is clicked', async () => {
    const { getWorkflows } = require('../../lib/api');
    
    render(<DashboardPage />);
    
    await waitFor(() => {
      expect(getWorkflows).toHaveBeenCalledTimes(1);
    });
    
    const refreshButton = screen.getByRole('button', { name: /refresh/i });
    fireEvent.click(refreshButton);
    
    await waitFor(() => {
      expect(getWorkflows).toHaveBeenCalledTimes(2);
    });
  });
});