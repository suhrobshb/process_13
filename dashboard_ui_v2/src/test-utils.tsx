/**
 * Test Utilities for React Components
 * ==================================
 * 
 * Custom render function with providers and utilities
 */

import React from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from 'next-themes';

// Mock providers for testing
const MockThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider attribute="class" defaultTheme="light">
    {children}
  </ThemeProvider>
);

const MockQueryClientProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
};

// All providers wrapper
const AllProviders: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <MockQueryClientProvider>
      <MockThemeProvider>
        {children}
      </MockThemeProvider>
    </MockQueryClientProvider>
  );
};

// Custom render function
const customRender = (
  ui: React.ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) => render(ui, { wrapper: AllProviders, ...options });

// Re-export everything from @testing-library/react
export * from '@testing-library/react';

// Override render method
export { customRender as render };

// Additional test utilities
export const createMockWorkflow = (overrides = {}) => ({
  id: 'test-workflow-1',
  name: 'Test Workflow',
  description: 'A test workflow for unit testing',
  status: 'active',
  created_at: '2023-01-01T00:00:00Z',
  updated_at: '2023-01-01T00:00:00Z',
  steps: [],
  ...overrides,
});

export const createMockExecution = (overrides = {}) => ({
  id: 'test-execution-1',
  workflow_id: 'test-workflow-1',
  status: 'running',
  started_at: '2023-01-01T00:00:00Z',
  completed_at: null,
  result: null,
  error: null,
  ...overrides,
});

export const createMockUser = (overrides = {}) => ({
  id: 'test-user-1',
  username: 'testuser',
  email: 'test@example.com',
  created_at: '2023-01-01T00:00:00Z',
  ...overrides,
});

// Mock API responses
export const mockApiResponse = (data: any, status = 200) => ({
  ok: status >= 200 && status < 300,
  status,
  statusText: status === 200 ? 'OK' : 'Error',
  json: () => Promise.resolve(data),
  text: () => Promise.resolve(JSON.stringify(data)),
});

// Wait for async operations
export const waitForLoadingToFinish = () => 
  new Promise(resolve => setTimeout(resolve, 0));

export default {
  render: customRender,
  createMockWorkflow,
  createMockExecution,
  createMockUser,
  mockApiResponse,
  waitForLoadingToFinish,
};