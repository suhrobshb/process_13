/**
 * Workflow Testing Panel
 * ======================
 * 
 * Comprehensive testing and validation system for workflows
 */

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Play,
  Square,
  CheckCircle,
  XCircle,
  AlertCircle,
  Clock,
  Target,
  Bug,
  Zap,
  BarChart3,
  FileCheck,
  TestTube,
  Eye,
  EyeOff,
  Download,
  Upload,
  RefreshCw,
  Settings,
  Filter,
  Search,
  Trash2,
  Copy,
  Save,
  Loader2,
} from 'lucide-react';
import { Node, Edge } from 'reactflow';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
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
} from '@/components/ui/dropdown-menu';
import { WorkflowNodeData } from './AdvancedWorkflowEditor';

// =============================================================================
// Types and Interfaces
// =============================================================================

export interface TestCase {
  id: string;
  name: string;
  description: string;
  inputs: Record<string, any>;
  expectedOutputs: Record<string, any>;
  status: 'pending' | 'running' | 'passed' | 'failed' | 'skipped';
  result?: TestResult;
  createdAt: string;
  updatedAt: string;
}

export interface TestResult {
  passed: boolean;
  executionTime: number;
  outputs: Record<string, any>;
  errors: string[];
  warnings: string[];
  nodeResults: Record<string, NodeTestResult>;
}

export interface NodeTestResult {
  nodeId: string;
  status: 'passed' | 'failed' | 'skipped';
  executionTime: number;
  input: any;
  output: any;
  error?: string;
}

export interface WorkflowValidation {
  isValid: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
  performance: PerformanceMetrics;
  coverage: CoverageMetrics;
}

export interface ValidationError {
  type: 'structure' | 'configuration' | 'dependency' | 'security';
  nodeId?: string;
  message: string;
  severity: 'error' | 'warning';
  suggestion?: string;
}

export interface ValidationWarning {
  type: 'performance' | 'best_practice' | 'accessibility';
  nodeId?: string;
  message: string;
  suggestion?: string;
}

export interface PerformanceMetrics {
  estimatedExecutionTime: number;
  complexityScore: number;
  resourceUsage: {
    cpu: number;
    memory: number;
    api_calls: number;
  };
}

export interface CoverageMetrics {
  nodesCovered: number;
  totalNodes: number;
  pathsCovered: number;
  totalPaths: number;
  branchCoverage: number;
}

// =============================================================================
// Test Case Management
// =============================================================================

const TestCaseCard: React.FC<{
  testCase: TestCase;
  onRun: (testCase: TestCase) => void;
  onEdit: (testCase: TestCase) => void;
  onDelete: (testCase: TestCase) => void;
  onDuplicate: (testCase: TestCase) => void;
}> = ({ testCase, onRun, onEdit, onDelete, onDuplicate }) => {
  const statusIcons = {
    pending: <Clock className="h-4 w-4 text-gray-500" />,
    running: <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />,
    passed: <CheckCircle className="h-4 w-4 text-green-500" />,
    failed: <XCircle className="h-4 w-4 text-red-500" />,
    skipped: <AlertCircle className="h-4 w-4 text-yellow-500" />,
  };

  const statusColors = {
    pending: 'border-gray-300 bg-gray-50',
    running: 'border-blue-300 bg-blue-50',
    passed: 'border-green-300 bg-green-50',
    failed: 'border-red-300 bg-red-50',
    skipped: 'border-yellow-300 bg-yellow-50',
  };

  return (
    <Card className={cn('cursor-pointer transition-all hover:shadow-md', statusColors[testCase.status])}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            {statusIcons[testCase.status]}
            <CardTitle className="text-sm font-medium">{testCase.name}</CardTitle>
          </div>
          <div className="flex items-center space-x-1">
            <Badge variant="outline" className="text-xs">
              {testCase.status}
            </Badge>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                  <Settings className="h-3 w-3" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => onRun(testCase)}>
                  <Play className="h-4 w-4 mr-2" />
                  Run Test
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onEdit(testCase)}>
                  <Eye className="h-4 w-4 mr-2" />
                  Edit
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onDuplicate(testCase)}>
                  <Copy className="h-4 w-4 mr-2" />
                  Duplicate
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onDelete(testCase)}>
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
        <CardDescription className="text-xs">{testCase.description}</CardDescription>
      </CardHeader>
      <CardContent className="pt-0">
        {testCase.result && (
          <div className="space-y-2 text-xs">
            <div className="flex justify-between">
              <span>Execution Time:</span>
              <span>{testCase.result.executionTime}ms</span>
            </div>
            {testCase.result.errors.length > 0 && (
              <div className="text-red-600">
                <div className="font-medium">Errors:</div>
                <ul className="list-disc list-inside space-y-1">
                  {testCase.result.errors.map((error, idx) => (
                    <li key={idx}>{error}</li>
                  ))}
                </ul>
              </div>
            )}
            {testCase.result.warnings.length > 0 && (
              <div className="text-yellow-600">
                <div className="font-medium">Warnings:</div>
                <ul className="list-disc list-inside space-y-1">
                  {testCase.result.warnings.map((warning, idx) => (
                    <li key={idx}>{warning}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

const TestCaseEditor: React.FC<{
  testCase: TestCase | null;
  onSave: (testCase: TestCase) => void;
  onCancel: () => void;
}> = ({ testCase, onSave, onCancel }) => {
  const [formData, setFormData] = useState<Partial<TestCase>>({
    name: '',
    description: '',
    inputs: {},
    expectedOutputs: {},
    ...testCase,
  });

  const handleSave = () => {
    const newTestCase: TestCase = {
      id: testCase?.id || Date.now().toString(),
      name: formData.name || 'Untitled Test',
      description: formData.description || '',
      inputs: formData.inputs || {},
      expectedOutputs: formData.expectedOutputs || {},
      status: 'pending',
      createdAt: testCase?.createdAt || new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    onSave(newTestCase);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">
          {testCase ? 'Edit Test Case' : 'Create Test Case'}
        </h3>
        <div className="flex items-center space-x-2">
          <Button variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button onClick={handleSave}>
            <Save className="h-4 w-4 mr-2" />
            Save
          </Button>
        </div>
      </div>

      <div className="space-y-4">
        <div>
          <label className="text-sm font-medium">Name</label>
          <Input
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            placeholder="Test case name"
          />
        </div>

        <div>
          <label className="text-sm font-medium">Description</label>
          <Textarea
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            placeholder="Test case description"
            rows={3}
          />
        </div>

        <div>
          <label className="text-sm font-medium">Input Data (JSON)</label>
          <Textarea
            value={JSON.stringify(formData.inputs, null, 2)}
            onChange={(e) => {
              try {
                const inputs = JSON.parse(e.target.value);
                setFormData({ ...formData, inputs });
              } catch (error) {
                // Invalid JSON, ignore
              }
            }}
            placeholder="Input data in JSON format"
            rows={6}
          />
        </div>

        <div>
          <label className="text-sm font-medium">Expected Outputs (JSON)</label>
          <Textarea
            value={JSON.stringify(formData.expectedOutputs, null, 2)}
            onChange={(e) => {
              try {
                const expectedOutputs = JSON.parse(e.target.value);
                setFormData({ ...formData, expectedOutputs });
              } catch (error) {
                // Invalid JSON, ignore
              }
            }}
            placeholder="Expected outputs in JSON format"
            rows={6}
          />
        </div>
      </div>
    </div>
  );
};

// =============================================================================
// Validation Panel
// =============================================================================

const ValidationPanel: React.FC<{
  validation: WorkflowValidation | null;
  onValidate: () => void;
  isValidating: boolean;
}> = ({ validation, onValidate, isValidating }) => {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Workflow Validation</h3>
        <Button onClick={onValidate} disabled={isValidating}>
          {isValidating ? (
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <FileCheck className="h-4 w-4 mr-2" />
          )}
          Validate
        </Button>
      </div>

      {validation && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Overall Status</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center space-x-2">
                  {validation.isValid ? (
                    <CheckCircle className="h-5 w-5 text-green-500" />
                  ) : (
                    <XCircle className="h-5 w-5 text-red-500" />
                  )}
                  <span className="font-medium">
                    {validation.isValid ? 'Valid' : 'Invalid'}
                  </span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Complexity Score</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {validation.performance.complexityScore}
                </div>
                <Progress value={validation.performance.complexityScore} className="mt-2" />
              </CardContent>
            </Card>
          </div>

          <Tabs defaultValue="errors" className="w-full">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="errors">
                Errors ({validation.errors.length})
              </TabsTrigger>
              <TabsTrigger value="warnings">
                Warnings ({validation.warnings.length})
              </TabsTrigger>
              <TabsTrigger value="performance">Performance</TabsTrigger>
              <TabsTrigger value="coverage">Coverage</TabsTrigger>
            </TabsList>

            <TabsContent value="errors" className="space-y-2">
              {validation.errors.length === 0 ? (
                <div className="text-center text-gray-500 py-8">
                  <CheckCircle className="h-12 w-12 mx-auto mb-2 text-green-500" />
                  <p>No errors found</p>
                </div>
              ) : (
                validation.errors.map((error, idx) => (
                  <Alert key={idx} variant="destructive">
                    <XCircle className="h-4 w-4" />
                    <AlertDescription>
                      <div className="space-y-1">
                        <div className="font-medium">{error.message}</div>
                        {error.suggestion && (
                          <div className="text-sm">💡 {error.suggestion}</div>
                        )}
                        {error.nodeId && (
                          <div className="text-xs">Node: {error.nodeId}</div>
                        )}
                      </div>
                    </AlertDescription>
                  </Alert>
                ))
              )}
            </TabsContent>

            <TabsContent value="warnings" className="space-y-2">
              {validation.warnings.length === 0 ? (
                <div className="text-center text-gray-500 py-8">
                  <CheckCircle className="h-12 w-12 mx-auto mb-2 text-green-500" />
                  <p>No warnings found</p>
                </div>
              ) : (
                validation.warnings.map((warning, idx) => (
                  <Alert key={idx}>
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      <div className="space-y-1">
                        <div className="font-medium">{warning.message}</div>
                        {warning.suggestion && (
                          <div className="text-sm">💡 {warning.suggestion}</div>
                        )}
                        {warning.nodeId && (
                          <div className="text-xs">Node: {warning.nodeId}</div>
                        )}
                      </div>
                    </AlertDescription>
                  </Alert>
                ))
              )}
            </TabsContent>

            <TabsContent value="performance" className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Estimated Execution Time</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {validation.performance.estimatedExecutionTime}ms
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Resource Usage</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>CPU:</span>
                      <span>{validation.performance.resourceUsage.cpu}%</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Memory:</span>
                      <span>{validation.performance.resourceUsage.memory}MB</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>API Calls:</span>
                      <span>{validation.performance.resourceUsage.api_calls}</span>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            <TabsContent value="coverage" className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Node Coverage</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {Math.round((validation.coverage.nodesCovered / validation.coverage.totalNodes) * 100)}%
                    </div>
                    <div className="text-sm text-gray-600">
                      {validation.coverage.nodesCovered} / {validation.coverage.totalNodes} nodes
                    </div>
                    <Progress 
                      value={(validation.coverage.nodesCovered / validation.coverage.totalNodes) * 100} 
                      className="mt-2" 
                    />
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Path Coverage</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {Math.round((validation.coverage.pathsCovered / validation.coverage.totalPaths) * 100)}%
                    </div>
                    <div className="text-sm text-gray-600">
                      {validation.coverage.pathsCovered} / {validation.coverage.totalPaths} paths
                    </div>
                    <Progress 
                      value={(validation.coverage.pathsCovered / validation.coverage.totalPaths) * 100} 
                      className="mt-2" 
                    />
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
          </Tabs>
        </div>
      )}
    </div>
  );
};

// =============================================================================
// Main Testing Panel Component
// =============================================================================

export const WorkflowTestingPanel: React.FC<{
  nodes: Node<WorkflowNodeData>[];
  edges: Edge[];
  onRunTest: (testCase: TestCase) => Promise<TestResult>;
  onValidateWorkflow: (nodes: Node<WorkflowNodeData>[], edges: Edge[]) => Promise<WorkflowValidation>;
}> = ({ nodes, edges, onRunTest, onValidateWorkflow }) => {
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [selectedTestCase, setSelectedTestCase] = useState<TestCase | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [validation, setValidation] = useState<WorkflowValidation | null>(null);
  const [isValidating, setIsValidating] = useState(false);
  const [isRunningTests, setIsRunningTests] = useState(false);
  const [testProgress, setTestProgress] = useState(0);

  const handleSaveTestCase = (testCase: TestCase) => {
    setTestCases(prev => {
      const existing = prev.find(t => t.id === testCase.id);
      if (existing) {
        return prev.map(t => t.id === testCase.id ? testCase : t);
      } else {
        return [...prev, testCase];
      }
    });
    setIsEditing(false);
    setSelectedTestCase(null);
  };

  const handleRunTest = async (testCase: TestCase) => {
    setTestCases(prev => prev.map(t => 
      t.id === testCase.id ? { ...t, status: 'running' } : t
    ));

    try {
      const result = await onRunTest(testCase);
      setTestCases(prev => prev.map(t => 
        t.id === testCase.id ? { 
          ...t, 
          status: result.passed ? 'passed' : 'failed', 
          result 
        } : t
      ));
      
      toast({
        title: result.passed ? "Test Passed" : "Test Failed",
        description: `${testCase.name} completed in ${result.executionTime}ms`,
        variant: result.passed ? "default" : "destructive",
      });
    } catch (error) {
      setTestCases(prev => prev.map(t => 
        t.id === testCase.id ? { ...t, status: 'failed' } : t
      ));
      
      toast({
        title: "Test Error",
        description: `Failed to run test: ${error}`,
        variant: "destructive",
      });
    }
  };

  const handleRunAllTests = async () => {
    setIsRunningTests(true);
    setTestProgress(0);
    
    const totalTests = testCases.length;
    
    for (let i = 0; i < totalTests; i++) {
      const testCase = testCases[i];
      await handleRunTest(testCase);
      setTestProgress(((i + 1) / totalTests) * 100);
    }
    
    setIsRunningTests(false);
  };

  const handleValidateWorkflow = async () => {
    setIsValidating(true);
    try {
      const result = await onValidateWorkflow(nodes, edges);
      setValidation(result);
      
      toast({
        title: "Validation Complete",
        description: result.isValid ? "Workflow is valid" : "Workflow has issues",
        variant: result.isValid ? "default" : "destructive",
      });
    } catch (error) {
      toast({
        title: "Validation Error",
        description: `Failed to validate workflow: ${error}`,
        variant: "destructive",
      });
    } finally {
      setIsValidating(false);
    }
  };

  const handleDeleteTestCase = (testCase: TestCase) => {
    setTestCases(prev => prev.filter(t => t.id !== testCase.id));
    toast({
      title: "Test Deleted",
      description: `Test case "${testCase.name}" has been deleted`,
    });
  };

  const handleDuplicateTestCase = (testCase: TestCase) => {
    const duplicate: TestCase = {
      ...testCase,
      id: Date.now().toString(),
      name: `${testCase.name} (Copy)`,
      status: 'pending',
      result: undefined,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    setTestCases(prev => [...prev, duplicate]);
    toast({
      title: "Test Duplicated",
      description: `Test case "${duplicate.name}" has been created`,
    });
  };

  const passedTests = testCases.filter(t => t.status === 'passed').length;
  const failedTests = testCases.filter(t => t.status === 'failed').length;
  const totalTests = testCases.length;

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between p-4 border-b">
        <h2 className="text-xl font-bold">Workflow Testing</h2>
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsEditing(true)}
          >
            <TestTube className="h-4 w-4 mr-2" />
            New Test
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRunAllTests}
            disabled={isRunningTests || testCases.length === 0}
          >
            {isRunningTests ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Play className="h-4 w-4 mr-2" />
            )}
            Run All
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-hidden">
        <Tabs defaultValue="tests" className="h-full flex flex-col">
          <TabsList className="mx-4 mt-4">
            <TabsTrigger value="tests">
              Test Cases ({totalTests})
            </TabsTrigger>
            <TabsTrigger value="validation">
              Validation
            </TabsTrigger>
            <TabsTrigger value="reports">
              Reports
            </TabsTrigger>
          </TabsList>

          <TabsContent value="tests" className="flex-1 overflow-hidden">
            <div className="h-full p-4">
              {isEditing ? (
                <TestCaseEditor
                  testCase={selectedTestCase}
                  onSave={handleSaveTestCase}
                  onCancel={() => {
                    setIsEditing(false);
                    setSelectedTestCase(null);
                  }}
                />
              ) : (
                <div className="space-y-4">
                  {isRunningTests && (
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium">Running Tests...</span>
                        <span className="text-sm">{Math.round(testProgress)}%</span>
                      </div>
                      <Progress value={testProgress} className="w-full" />
                    </div>
                  )}

                  {totalTests > 0 && (
                    <div className="grid grid-cols-3 gap-4">
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm">Total Tests</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="text-2xl font-bold">{totalTests}</div>
                        </CardContent>
                      </Card>
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm">Passed</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="text-2xl font-bold text-green-600">{passedTests}</div>
                        </CardContent>
                      </Card>
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm">Failed</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="text-2xl font-bold text-red-600">{failedTests}</div>
                        </CardContent>
                      </Card>
                    </div>
                  )}

                  <div className="space-y-4">
                    {testCases.length === 0 ? (
                      <div className="text-center text-gray-500 py-12">
                        <TestTube className="h-16 w-16 mx-auto mb-4 opacity-50" />
                        <p className="text-lg font-medium">No test cases yet</p>
                        <p className="text-sm">Create your first test case to get started</p>
                        <Button
                          onClick={() => setIsEditing(true)}
                          className="mt-4"
                        >
                          Create Test Case
                        </Button>
                      </div>
                    ) : (
                      testCases.map((testCase) => (
                        <TestCaseCard
                          key={testCase.id}
                          testCase={testCase}
                          onRun={handleRunTest}
                          onEdit={(tc) => {
                            setSelectedTestCase(tc);
                            setIsEditing(true);
                          }}
                          onDelete={handleDeleteTestCase}
                          onDuplicate={handleDuplicateTestCase}
                        />
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="validation" className="flex-1 overflow-hidden">
            <div className="h-full p-4">
              <ValidationPanel
                validation={validation}
                onValidate={handleValidateWorkflow}
                isValidating={isValidating}
              />
            </div>
          </TabsContent>

          <TabsContent value="reports" className="flex-1 overflow-hidden">
            <div className="h-full p-4">
              <div className="text-center text-gray-500 py-12">
                <BarChart3 className="h-16 w-16 mx-auto mb-4 opacity-50" />
                <p className="text-lg font-medium">Test Reports</p>
                <p className="text-sm">Detailed test execution reports will appear here</p>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default WorkflowTestingPanel;