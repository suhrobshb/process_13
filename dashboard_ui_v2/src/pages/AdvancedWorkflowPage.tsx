/**
 * Advanced Workflow Page
 * ======================
 * 
 * Complete workflow management interface with advanced editor and testing
 */

import React, { useState, useEffect } from 'react';
import { useParams, useLocation } from 'wouter';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Save,
  Play,
  Settings,
  TestTube,
  Eye,
  EyeOff,
  Maximize2,
  Minimize2,
  Download,
  Upload,
  Share2,
  History,
  Bell,
  Users,
  Lock,
  Globe,
  ChevronDown,
  Loader2,
  CheckCircle,
  XCircle,
  AlertCircle,
  Clock,
  Zap,
  BarChart3,
  GitBranch,
  Layers,
  Target,
  Activity,
} from 'lucide-react';
import { Node, Edge } from 'reactflow';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { toast } from '@/components/ui/use-toast';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';

import { AdvancedWorkflowEditor, WorkflowNodeData } from '@/components/workflow-editor/AdvancedWorkflowEditor';
import { WorkflowTestingPanel, TestCase, TestResult, WorkflowValidation } from '@/components/workflow-editor/WorkflowTestingPanel';
import { apiClient, queryKeys } from '@/lib/api';

// =============================================================================
// Types and Interfaces
// =============================================================================

interface WorkflowMetadata {
  id: string;
  name: string;
  description: string;
  status: 'draft' | 'active' | 'paused' | 'archived';
  visibility: 'private' | 'team' | 'public';
  tags: string[];
  createdAt: string;
  updatedAt: string;
  createdBy: string;
  version: number;
  metrics: {
    totalRuns: number;
    successRate: number;
    avgExecutionTime: number;
    lastRun?: string;
  };
}

interface ExecutionResult {
  id: string;
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  startTime: string;
  endTime?: string;
  executionTime?: number;
  nodeResults: Record<string, any>;
  output?: any;
  error?: string;
}

// =============================================================================
// Workflow Header Component
// =============================================================================

const WorkflowHeader: React.FC<{
  workflow: WorkflowMetadata;
  onUpdateWorkflow: (updates: Partial<WorkflowMetadata>) => void;
  onExecute: () => void;
  onSave: () => void;
  isExecuting: boolean;
  isSaving: boolean;
  hasUnsavedChanges: boolean;
}> = ({ workflow, onUpdateWorkflow, onExecute, onSave, isExecuting, isSaving, hasUnsavedChanges }) => {
  const [isEditingName, setIsEditingName] = useState(false);
  const [workflowName, setWorkflowName] = useState(workflow.name);

  const handleNameSave = () => {
    onUpdateWorkflow({ name: workflowName });
    setIsEditingName(false);
  };

  const statusColors = {
    draft: 'bg-gray-100 text-gray-800',
    active: 'bg-green-100 text-green-800',
    paused: 'bg-yellow-100 text-yellow-800',
    archived: 'bg-red-100 text-red-800',
  };

  const visibilityIcons = {
    private: <Lock className="h-4 w-4" />,
    team: <Users className="h-4 w-4" />,
    public: <Globe className="h-4 w-4" />,
  };

  return (
    <div className="bg-white border-b px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            {isEditingName ? (
              <div className="flex items-center space-x-2">
                <Input
                  value={workflowName}
                  onChange={(e) => setWorkflowName(e.target.value)}
                  onBlur={handleNameSave}
                  onKeyPress={(e) => e.key === 'Enter' && handleNameSave()}
                  className="text-2xl font-bold"
                  autoFocus
                />
                <Button size="sm" onClick={handleNameSave}>
                  Save
                </Button>
              </div>
            ) : (
              <h1 
                className="text-2xl font-bold cursor-pointer hover:text-blue-600"
                onClick={() => setIsEditingName(true)}
              >
                {workflow.name}
              </h1>
            )}
            {hasUnsavedChanges && (
              <Badge variant="outline" className="text-orange-600">
                Unsaved changes
              </Badge>
            )}
          </div>
          
          <div className="flex items-center space-x-2">
            <Badge className={statusColors[workflow.status]}>
              {workflow.status}
            </Badge>
            <Badge variant="outline" className="flex items-center space-x-1">
              {visibilityIcons[workflow.visibility]}
              <span>{workflow.visibility}</span>
            </Badge>
            <Badge variant="outline">
              v{workflow.version}
            </Badge>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm">
                <Settings className="h-4 w-4 mr-2" />
                Settings
                <ChevronDown className="h-4 w-4 ml-2" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem>
                <History className="h-4 w-4 mr-2" />
                Version History
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Share2 className="h-4 w-4 mr-2" />
                Share Workflow
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Download className="h-4 w-4 mr-2" />
                Export
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Upload className="h-4 w-4 mr-2" />
                Import
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem>
                <Bell className="h-4 w-4 mr-2" />
                Notifications
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          <Button
            variant="outline"
            size="sm"
            onClick={onExecute}
            disabled={isExecuting}
          >
            {isExecuting ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Play className="h-4 w-4 mr-2" />
            )}
            Execute
          </Button>

          <Button
            onClick={onSave}
            disabled={isSaving || !hasUnsavedChanges}
            size="sm"
          >
            {isSaving ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Save className="h-4 w-4 mr-2" />
            )}
            Save
          </Button>
        </div>
      </div>

      {workflow.description && (
        <div className="mt-2">
          <p className="text-gray-600 text-sm">{workflow.description}</p>
        </div>
      )}

      <div className="mt-4 flex items-center space-x-6 text-sm text-gray-600">
        <div className="flex items-center space-x-1">
          <Activity className="h-4 w-4" />
          <span>{workflow.metrics.totalRuns} runs</span>
        </div>
        <div className="flex items-center space-x-1">
          <Target className="h-4 w-4" />
          <span>{workflow.metrics.successRate}% success rate</span>
        </div>
        <div className="flex items-center space-x-1">
          <Clock className="h-4 w-4" />
          <span>Avg: {workflow.metrics.avgExecutionTime}ms</span>
        </div>
        {workflow.metrics.lastRun && (
          <div className="flex items-center space-x-1">
            <History className="h-4 w-4" />
            <span>Last run: {new Date(workflow.metrics.lastRun).toLocaleString()}</span>
          </div>
        )}
      </div>
    </div>
  );
};

// =============================================================================
// Workflow Metrics Panel
// =============================================================================

const WorkflowMetricsPanel: React.FC<{
  workflow: WorkflowMetadata;
  executionHistory: ExecutionResult[];
}> = ({ workflow, executionHistory }) => {
  const recentExecutions = executionHistory.slice(0, 5);
  const successfulRuns = executionHistory.filter(r => r.status === 'completed').length;
  const failedRuns = executionHistory.filter(r => r.status === 'failed').length;

  const statusIcons = {
    running: <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />,
    completed: <CheckCircle className="h-4 w-4 text-green-500" />,
    failed: <XCircle className="h-4 w-4 text-red-500" />,
    cancelled: <AlertCircle className="h-4 w-4 text-yellow-500" />,
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Total Executions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{executionHistory.length}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Success Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {executionHistory.length > 0 ? Math.round((successfulRuns / executionHistory.length) * 100) : 0}%
            </div>
            <Progress 
              value={executionHistory.length > 0 ? (successfulRuns / executionHistory.length) * 100 : 0} 
              className="mt-2"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Avg Execution Time</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {workflow.metrics.avgExecutionTime}ms
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Failed Runs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{failedRuns}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Recent Executions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {recentExecutions.length === 0 ? (
              <div className="text-center text-gray-500 py-4">
                <Activity className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No executions yet</p>
              </div>
            ) : (
              recentExecutions.map((execution) => (
                <div key={execution.id} className="flex items-center justify-between py-2 border-b last:border-b-0">
                  <div className="flex items-center space-x-3">
                    {statusIcons[execution.status]}
                    <div>
                      <div className="text-sm font-medium">{execution.id}</div>
                      <div className="text-xs text-gray-500">
                        {new Date(execution.startTime).toLocaleString()}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-medium">
                      {execution.executionTime ? `${execution.executionTime}ms` : '-'}
                    </div>
                    <div className="text-xs text-gray-500 capitalize">
                      {execution.status}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

// =============================================================================
// Main Advanced Workflow Page Component
// =============================================================================

export const AdvancedWorkflowPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [, setLocation] = useLocation();
  const queryClient = useQueryClient();

  const [nodes, setNodes] = useState<Node<WorkflowNodeData>[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [activeTab, setActiveTab] = useState('editor');
  const [isExecuting, setIsExecuting] = useState(false);
  const [currentExecution, setCurrentExecution] = useState<ExecutionResult | null>(null);

  // Fetch workflow data
  const { data: workflow, isLoading, error } = useQuery({
    queryKey: queryKeys.workflow(id),
    queryFn: () => apiClient.getWorkflow(id),
    enabled: !!id,
  });

  // Fetch execution history
  const { data: executionHistory = [] } = useQuery({
    queryKey: queryKeys.workflowExecutions(id),
    queryFn: () => apiClient.getWorkflowExecutions(id),
    enabled: !!id,
  });

  // Save workflow mutation
  const saveMutation = useMutation({
    mutationFn: (updates: { nodes: Node<WorkflowNodeData>[], edges: Edge[] }) => {
      return apiClient.updateWorkflow(id, updates);
    },
    onSuccess: () => {
      setHasUnsavedChanges(false);
      toast({
        title: "Workflow Saved",
        description: "Your changes have been saved successfully",
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.workflow(id) });
    },
    onError: (error) => {
      toast({
        title: "Save Failed",
        description: "Failed to save workflow changes",
        variant: "destructive",
      });
    },
  });

  // Execute workflow mutation
  const executeMutation = useMutation({
    mutationFn: () => apiClient.executeWorkflow(id),
    onSuccess: (result) => {
      setCurrentExecution(result);
      setIsExecuting(false);
      toast({
        title: "Workflow Executed",
        description: "Workflow execution completed successfully",
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.workflowExecutions(id) });
    },
    onError: (error) => {
      setIsExecuting(false);
      toast({
        title: "Execution Failed",
        description: "Failed to execute workflow",
        variant: "destructive",
      });
    },
  });

  // Update workflow metadata mutation
  const updateWorkflowMutation = useMutation({
    mutationFn: (updates: Partial<WorkflowMetadata>) => {
      return apiClient.updateWorkflow(id, updates);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.workflow(id) });
    },
  });

  useEffect(() => {
    if (workflow) {
      setNodes(workflow.nodes || []);
      setEdges(workflow.edges || []);
    }
  }, [workflow]);

  const handleSave = () => {
    saveMutation.mutate({ nodes, edges });
  };

  const handleExecute = () => {
    setIsExecuting(true);
    executeMutation.mutate();
  };

  const handleUpdateWorkflow = (updates: Partial<WorkflowMetadata>) => {
    updateWorkflowMutation.mutate(updates);
  };

  const handleNodesChange = (newNodes: Node<WorkflowNodeData>[]) => {
    setNodes(newNodes);
    setHasUnsavedChanges(true);
  };

  const handleEdgesChange = (newEdges: Edge[]) => {
    setEdges(newEdges);
    setHasUnsavedChanges(true);
  };

  const handleRunTest = async (testCase: TestCase): Promise<TestResult> => {
    // Mock test execution
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    const passed = Math.random() > 0.3; // 70% success rate
    const executionTime = Math.random() * 5000 + 1000;
    
    return {
      passed,
      executionTime,
      outputs: { result: "Test output" },
      errors: passed ? [] : ["Test assertion failed"],
      warnings: ["Performance warning"],
      nodeResults: {},
    };
  };

  const handleValidateWorkflow = async (
    nodes: Node<WorkflowNodeData>[], 
    edges: Edge[]
  ): Promise<WorkflowValidation> => {
    // Mock validation
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    const errors = [];
    const warnings = [];
    
    // Check for basic structure issues
    if (nodes.length === 0) {
      errors.push({
        type: 'structure' as const,
        message: 'Workflow must contain at least one node',
        severity: 'error' as const,
      });
    }
    
    const startNodes = nodes.filter(n => n.data.type === 'start');
    if (startNodes.length === 0) {
      errors.push({
        type: 'structure' as const,
        message: 'Workflow must have a start node',
        severity: 'error' as const,
      });
    }
    
    const endNodes = nodes.filter(n => n.data.type === 'end');
    if (endNodes.length === 0) {
      warnings.push({
        type: 'best_practice' as const,
        message: 'Consider adding an end node',
        suggestion: 'Add an end node to clearly define workflow completion',
      });
    }
    
    // Check for orphaned nodes
    const connectedNodes = new Set();
    edges.forEach(edge => {
      connectedNodes.add(edge.source);
      connectedNodes.add(edge.target);
    });
    
    const orphanedNodes = nodes.filter(n => !connectedNodes.has(n.id) && n.data.type !== 'start');
    orphanedNodes.forEach(node => {
      warnings.push({
        type: 'structure' as const,
        nodeId: node.id,
        message: `Node "${node.data.label}" is not connected`,
        suggestion: 'Connect this node to the workflow or remove it',
      });
    });
    
    return {
      isValid: errors.length === 0,
      errors,
      warnings,
      performance: {
        estimatedExecutionTime: nodes.length * 500 + Math.random() * 2000,
        complexityScore: Math.min(nodes.length * 5 + edges.length * 2, 100),
        resourceUsage: {
          cpu: Math.random() * 30 + 10,
          memory: Math.random() * 100 + 50,
          api_calls: nodes.filter(n => n.data.type === 'api').length,
        },
      },
      coverage: {
        nodesCovered: Math.min(nodes.length, Math.floor(nodes.length * 0.8)),
        totalNodes: nodes.length,
        pathsCovered: Math.min(edges.length, Math.floor(edges.length * 0.9)),
        totalPaths: edges.length,
        branchCoverage: Math.random() * 40 + 60,
      },
    };
  };

  if (isLoading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="space-y-4 text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto" />
          <p className="text-gray-600">Loading workflow...</p>
        </div>
      </div>
    );
  }

  if (error || !workflow) {
    return (
      <div className="h-screen flex items-center justify-center">
        <Alert variant="destructive" className="max-w-md">
          <XCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to load workflow. Please try again.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      <WorkflowHeader
        workflow={workflow}
        onUpdateWorkflow={handleUpdateWorkflow}
        onExecute={handleExecute}
        onSave={handleSave}
        isExecuting={isExecuting}
        isSaving={saveMutation.isPending}
        hasUnsavedChanges={hasUnsavedChanges}
      />

      <div className="flex-1 overflow-hidden">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col">
          <div className="bg-white border-b px-6">
            <TabsList className="mt-4">
              <TabsTrigger value="editor" className="flex items-center space-x-2">
                <GitBranch className="h-4 w-4" />
                <span>Editor</span>
              </TabsTrigger>
              <TabsTrigger value="testing" className="flex items-center space-x-2">
                <TestTube className="h-4 w-4" />
                <span>Testing</span>
              </TabsTrigger>
              <TabsTrigger value="metrics" className="flex items-center space-x-2">
                <BarChart3 className="h-4 w-4" />
                <span>Metrics</span>
              </TabsTrigger>
              <TabsTrigger value="versions" className="flex items-center space-x-2">
                <History className="h-4 w-4" />
                <span>Versions</span>
              </TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="editor" className="flex-1 overflow-hidden m-0 p-0">
            <AdvancedWorkflowEditor
              workflowId={id}
              initialNodes={nodes}
              initialEdges={edges}
              onSave={(newNodes, newEdges) => {
                setNodes(newNodes);
                setEdges(newEdges);
                handleSave();
              }}
            />
          </TabsContent>

          <TabsContent value="testing" className="flex-1 overflow-hidden m-0 p-0">
            <WorkflowTestingPanel
              nodes={nodes}
              edges={edges}
              onRunTest={handleRunTest}
              onValidateWorkflow={handleValidateWorkflow}
            />
          </TabsContent>

          <TabsContent value="metrics" className="flex-1 overflow-hidden m-0 p-0">
            <div className="h-full p-6">
              <WorkflowMetricsPanel
                workflow={workflow}
                executionHistory={executionHistory}
              />
            </div>
          </TabsContent>

          <TabsContent value="versions" className="flex-1 overflow-hidden m-0 p-0">
            <div className="h-full p-6">
              <div className="text-center text-gray-500 py-12">
                <History className="h-16 w-16 mx-auto mb-4 opacity-50" />
                <p className="text-lg font-medium">Version History</p>
                <p className="text-sm">Track changes and manage workflow versions</p>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default AdvancedWorkflowPage;