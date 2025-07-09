/**
 * API Client for Process 13
 * ==========================
 * 
 * Centralized API client with TypeScript support and error handling
 */

import { toast } from '@/components/ui/use-toast';

const API_BASE = 'http://localhost:8000';

// Types
export interface DashboardStats {
  workflows_count: number;
  hours_saved: number;
  process_accuracy: number;
  executions_today: number;
  total_tasks: number;
  active_workflows: number;
}

export interface RecentWorkflow {
  id: number;
  name: string;
  status: string;
  last_run: string;
  efficiency: number;
  created_at: string;
}

export interface SystemHealth {
  api_status: string;
  database_status: string;
  ai_engine_status: string;
  redis_status: string;
  overall_status: string;
  uptime: string;
}

export interface RecordingSession {
  session_id: string;
  workflow_name: string;
  status: string;
  started_at: string;
}

export interface NLPResponse {
  parsed_intent: string;
  workflow_suggestion: any;
  confidence: number;
}

export interface ROIAnalytics {
  total_cost_savings: number;
  automation_rate: number;
  time_saved_hours: number;
  error_reduction: number;
  monthly_trends: Array<{
    month: string;
    savings: number;
    hours: number;
  }>;
}

export interface PerformanceMetrics {
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  network_throughput: number;
  response_times: {
    avg: number;
    p95: number;
    p99: number;
  };
  error_rates: {
    api: number;
    workflows: number;
    executions: number;
  };
}

// API Client Class
class APIClient {
  private baseURL: string;
  private authToken: string | null = null;

  constructor(baseURL: string = API_BASE) {
    this.baseURL = baseURL;
  }

  setAuthToken(token: string | null) {
    this.authToken = token;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...(this.authToken && { 'Authorization': `Bearer ${this.authToken}` }),
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          `API Error: ${response.status} - ${errorData.detail || response.statusText}`
        );
      }

      return await response.json();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      toast({
        title: "API Error",
        description: message,
        variant: "destructive",
      });
      throw error;
    }
  }

  // Authentication APIs
  async login(credentials: { email: string; password: string; rememberMe?: boolean }): Promise<{ user: any; token: string; refreshToken: string }> {
    return this.request<{ user: any; token: string; refreshToken: string }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
  }

  async register(data: { email: string; password: string; name: string; confirmPassword: string }): Promise<{ user: any; token: string; refreshToken: string }> {
    return this.request<{ user: any; token: string; refreshToken: string }>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async refreshToken(refreshToken: string): Promise<{ user: any; token: string; refreshToken: string }> {
    return this.request<{ user: any; token: string; refreshToken: string }>('/api/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  }

  async validateToken(token: string): Promise<any> {
    return this.request<any>('/api/auth/validate', {
      headers: { 'Authorization': `Bearer ${token}` },
    });
  }

  async logout(): Promise<void> {
    return this.request<void>('/api/auth/logout', {
      method: 'POST',
    });
  }

  async updateProfile(updates: any): Promise<any> {
    return this.request<any>('/api/auth/profile', {
      method: 'PUT',
      body: JSON.stringify(updates),
    });
  }

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    return this.request<void>('/api/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    });
  }

  // Dashboard APIs
  async getDashboardStats(): Promise<DashboardStats> {
    return this.request<DashboardStats>('/api/dashboard/stats');
  }

  async getRecentWorkflows(): Promise<RecentWorkflow[]> {
    return this.request<RecentWorkflow[]>('/api/dashboard/recent-workflows');
  }

  // System Health
  async getSystemHealth(): Promise<SystemHealth> {
    return this.request<SystemHealth>('/api/system/health/detailed');
  }

  async getSystemMetrics(): Promise<any> {
    return this.request<any>('/api/system/metrics');
  }

  // Recording Studio
  async startRecording(workflowName: string): Promise<RecordingSession> {
    return this.request<RecordingSession>('/api/recording/start', {
      method: 'POST',
      body: JSON.stringify({ workflow_name: workflowName }),
    });
  }

  async stopRecording(sessionId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/recording/stop/${sessionId}`, {
      method: 'POST',
    });
  }

  async getRecordingStatus(sessionId: string): Promise<RecordingSession> {
    return this.request<RecordingSession>(`/api/recording/status/${sessionId}`);
  }

  // NLP Processing
  async parseNLPCommand(command: string): Promise<NLPResponse> {
    return this.request<NLPResponse>('/api/nlp/parse-command', {
      method: 'POST',
      body: JSON.stringify({ command }),
    });
  }

  // Analytics
  async getROIAnalytics(): Promise<ROIAnalytics> {
    return this.request<ROIAnalytics>('/api/analytics/roi');
  }

  async getPerformanceMetrics(): Promise<PerformanceMetrics> {
    return this.request<PerformanceMetrics>('/api/analytics/performance');
  }

  // Workflow Management
  async getWorkflows(): Promise<any[]> {
    return this.request<any[]>('/api/workflows');
  }

  async getWorkflow(id: number): Promise<any> {
    return this.request<any>(`/api/workflows/${id}`);
  }

  async createWorkflow(workflow: any): Promise<any> {
    return this.request<any>('/api/workflows', {
      method: 'POST',
      body: JSON.stringify(workflow),
    });
  }

  async updateWorkflow(id: number | string, workflow: any): Promise<any> {
    return this.request<any>(`/api/workflows/${id}`, {
      method: 'PUT',
      body: JSON.stringify(workflow),
    });
  }

  async executeWorkflow(id: number | string): Promise<any> {
    return this.request<any>(`/api/workflows/${id}/execute`, {
      method: 'POST',
    });
  }

  async getWorkflowExecutions(id: number | string): Promise<any[]> {
    return this.request<any[]>(`/api/workflows/${id}/executions`);
  }

  // Task Management
  async getTasks(): Promise<any[]> {
    return this.request<any[]>('/api/tasks');
  }

  async getTask(id: number): Promise<any> {
    return this.request<any>(`/api/tasks/${id}`);
  }

  // Execution Management
  async getExecutions(): Promise<any[]> {
    return this.request<any[]>('/api/executions');
  }

  async getExecution(id: number): Promise<any> {
    return this.request<any>(`/api/executions/${id}`);
  }

  async createExecution(execution: any): Promise<any> {
    return this.request<any>('/api/executions', {
      method: 'POST',
      body: JSON.stringify(execution),
    });
  }

  // Health Check
  async healthCheck(): Promise<{ status: string }> {
    return this.request<{ status: string }>('/health');
  }

  async ping(): Promise<{ message: string }> {
    return this.request<{ message: string }>('/ping');
  }
}

// WebSocket Client
export class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  constructor(url: string = 'ws://localhost:8000/ws/notifications') {
    this.url = url;
  }

  connect(onMessage?: (data: any) => void, onError?: (error: Event) => void) {
    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
        toast({
          title: "Connected",
          description: "Real-time updates enabled",
        });
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessage?.(data);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        this.attemptReconnect(onMessage, onError);
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        onError?.(error);
      };
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      onError?.(error as Event);
    }
  }

  private attemptReconnect(onMessage?: (data: any) => void, onError?: (error: Event) => void) {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
      
      setTimeout(() => {
        console.log(`Attempting WebSocket reconnect ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
        this.connect(onMessage, onError);
      }, delay);
    } else {
      toast({
        title: "Connection Lost",
        description: "Unable to reconnect to real-time updates",
        variant: "destructive",
      });
    }
  }

  send(data: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}

// Export singleton instance
export const apiClient = new APIClient();
export const wsClient = new WebSocketClient();

// React Query keys
export const queryKeys = {
  dashboardStats: ['dashboard', 'stats'],
  recentWorkflows: ['dashboard', 'workflows'],
  systemHealth: ['system', 'health'],
  systemMetrics: ['system', 'metrics'],
  roiAnalytics: ['analytics', 'roi'],
  performanceMetrics: ['analytics', 'performance'],
  workflows: ['workflows'],
  workflow: (id: number | string) => ['workflows', id],
  workflowExecutions: (id: number | string) => ['workflows', id, 'executions'],
  tasks: ['tasks'],
  task: (id: number) => ['tasks', id],
  executions: ['executions'],
  execution: (id: number) => ['executions', id],
  // Authentication keys
  user: ['auth', 'user'],
  profile: ['auth', 'profile'],
} as const;