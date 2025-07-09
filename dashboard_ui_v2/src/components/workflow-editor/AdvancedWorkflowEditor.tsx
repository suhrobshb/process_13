/**
 * Advanced Workflow Editor
 * ========================
 * 
 * Enhanced drag-and-drop workflow builder with advanced features
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  MiniMap,
  Handle,
  Position,
  ConnectionLineType,
  BackgroundVariant,
  Node,
  Edge,
  Connection,
  NodeTypes,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Bot,
  Cpu,
  Mail,
  GitBranch,
  FileText,
  Database,
  Play,
  Save,
  Upload,
  Download,
  Trash2,
  ChevronDown,
  Code2,
  Loader2,
  AlertCircle,
  Settings,
  Timer,
  CheckCircle,
  XCircle,
  PlusCircle,
  Workflow,
  Zap,
  Clock,
  Search,
  Filter,
  Eye,
  EyeOff,
  Copy,
  Scissors,
  Grid,
  Maximize2,
  Minimize2,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { v4 as uuidv4 } from 'uuid';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { toast } from '@/components/ui/use-toast';
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { apiClient } from '@/lib/api';

// =============================================================================
// Enhanced Type Definitions
// =============================================================================

export interface WorkflowNodeData {
  id: string;
  label: string;
  type: NodeType;
  category: NodeCategory;
  icon: React.ReactNode;
  description: string;
  status: NodeStatus;
  config: Record<string, any>;
  inputs: NodePort[];
  outputs: NodePort[];
  validation?: ValidationResult;
  metrics?: NodeMetrics;
}

export type NodeType = 
  | 'start' | 'end' 
  | 'action' | 'decision' | 'loop' | 'parallel' | 'delay'
  | 'llm' | 'api' | 'database' | 'file' | 'email' | 'webhook'
  | 'script' | 'condition' | 'transform' | 'validation';

export type NodeCategory = 'control' | 'ai' | 'integration' | 'processing' | 'io';

export type NodeStatus = 'idle' | 'running' | 'completed' | 'failed' | 'paused';

export interface NodePort {
  id: string;
  label: string;
  type: 'input' | 'output';
  dataType: string;
  required?: boolean;
}

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

export interface NodeMetrics {
  executionTime?: number;
  successRate?: number;
  lastRun?: string;
  avgResponseTime?: number;
}

// =============================================================================
// Node Template Library
// =============================================================================

const NODE_TEMPLATES: Record<NodeType, Partial<WorkflowNodeData>> = {
  start: {
    label: 'Start',
    type: 'start',
    category: 'control',
    icon: <Play className="h-5 w-5" />,
    description: 'Workflow entry point',
    outputs: [{ id: 'output', label: 'Next', type: 'output', dataType: 'trigger' }],
  },
  end: {
    label: 'End',
    type: 'end',
    category: 'control',
    icon: <CheckCircle className="h-5 w-5" />,
    description: 'Workflow exit point',
    inputs: [{ id: 'input', label: 'Previous', type: 'input', dataType: 'trigger' }],
  },
  action: {
    label: 'Action',
    type: 'action',
    category: 'processing',
    icon: <Zap className="h-5 w-5" />,
    description: 'Perform an action',
    inputs: [{ id: 'input', label: 'Trigger', type: 'input', dataType: 'trigger' }],
    outputs: [{ id: 'output', label: 'Result', type: 'output', dataType: 'any' }],
  },
  decision: {
    label: 'Decision',
    type: 'decision',
    category: 'control',
    icon: <GitBranch className="h-5 w-5" />,
    description: 'Conditional branching',
    inputs: [{ id: 'input', label: 'Condition', type: 'input', dataType: 'boolean' }],
    outputs: [
      { id: 'true', label: 'True', type: 'output', dataType: 'trigger' },
      { id: 'false', label: 'False', type: 'output', dataType: 'trigger' },
    ],
  },
  llm: {
    label: 'LLM',
    type: 'llm',
    category: 'ai',
    icon: <Bot className="h-5 w-5" />,
    description: 'AI language model processing',
    inputs: [{ id: 'prompt', label: 'Prompt', type: 'input', dataType: 'string' }],
    outputs: [{ id: 'response', label: 'Response', type: 'output', dataType: 'string' }],
    config: {
      provider: 'openai',
      model: 'gpt-4',
      temperature: 0.7,
      maxTokens: 1000,
    },
  },
  api: {
    label: 'API Call',
    type: 'api',
    category: 'integration',
    icon: <Database className="h-5 w-5" />,
    description: 'HTTP API request',
    inputs: [{ id: 'data', label: 'Data', type: 'input', dataType: 'object' }],
    outputs: [{ id: 'response', label: 'Response', type: 'output', dataType: 'object' }],
  },
  email: {
    label: 'Email',
    type: 'email',
    category: 'integration',
    icon: <Mail className="h-5 w-5" />,
    description: 'Send email notification',
    inputs: [{ id: 'content', label: 'Content', type: 'input', dataType: 'string' }],
    outputs: [{ id: 'sent', label: 'Sent', type: 'output', dataType: 'boolean' }],
  },
  delay: {
    label: 'Delay',
    type: 'delay',
    category: 'control',
    icon: <Timer className="h-5 w-5" />,
    description: 'Wait for specified duration',
    inputs: [{ id: 'trigger', label: 'Trigger', type: 'input', dataType: 'trigger' }],
    outputs: [{ id: 'continue', label: 'Continue', type: 'output', dataType: 'trigger' }],
  },
  script: {
    label: 'Script',
    type: 'script',
    category: 'processing',
    icon: <Code2 className="h-5 w-5" />,
    description: 'Execute custom script',
    inputs: [{ id: 'input', label: 'Input', type: 'input', dataType: 'any' }],
    outputs: [{ id: 'output', label: 'Output', type: 'output', dataType: 'any' }],
  },
  file: {
    label: 'File',
    type: 'file',
    category: 'io',
    icon: <FileText className="h-5 w-5" />,
    description: 'File operations',
    inputs: [{ id: 'path', label: 'Path', type: 'input', dataType: 'string' }],
    outputs: [{ id: 'content', label: 'Content', type: 'output', dataType: 'string' }],
  },
  loop: {
    label: 'Loop',
    type: 'loop',
    category: 'control',
    icon: <Grid className="h-5 w-5" />,
    description: 'Iterate over items',
    inputs: [{ id: 'items', label: 'Items', type: 'input', dataType: 'array' }],
    outputs: [{ id: 'item', label: 'Item', type: 'output', dataType: 'any' }],
  },
  parallel: {
    label: 'Parallel',
    type: 'parallel',
    category: 'control',
    icon: <Maximize2 className="h-5 w-5" />,
    description: 'Execute branches in parallel',
    inputs: [{ id: 'input', label: 'Input', type: 'input', dataType: 'trigger' }],
    outputs: [
      { id: 'branch1', label: 'Branch 1', type: 'output', dataType: 'trigger' },
      { id: 'branch2', label: 'Branch 2', type: 'output', dataType: 'trigger' },
    ],
  },
  webhook: {
    label: 'Webhook',
    type: 'webhook',
    category: 'integration',
    icon: <Workflow className="h-5 w-5" />,
    description: 'HTTP webhook endpoint',
    outputs: [{ id: 'payload', label: 'Payload', type: 'output', dataType: 'object' }],
  },
  database: {
    label: 'Database',
    type: 'database',
    category: 'integration',
    icon: <Database className="h-5 w-5" />,
    description: 'Database operations',
    inputs: [{ id: 'query', label: 'Query', type: 'input', dataType: 'string' }],
    outputs: [{ id: 'result', label: 'Result', type: 'output', dataType: 'array' }],
  },
  condition: {
    label: 'Condition',
    type: 'condition',
    category: 'control',
    icon: <Search className="h-5 w-5" />,
    description: 'Evaluate condition',
    inputs: [{ id: 'input', label: 'Input', type: 'input', dataType: 'any' }],
    outputs: [{ id: 'result', label: 'Result', type: 'output', dataType: 'boolean' }],
  },
  transform: {
    label: 'Transform',
    type: 'transform',
    category: 'processing',
    icon: <Scissors className="h-5 w-5" />,
    description: 'Transform data',
    inputs: [{ id: 'input', label: 'Input', type: 'input', dataType: 'any' }],
    outputs: [{ id: 'output', label: 'Output', type: 'output', dataType: 'any' }],
  },
  validation: {
    label: 'Validation',
    type: 'validation',
    category: 'processing',
    icon: <CheckCircle className="h-5 w-5" />,
    description: 'Validate data',
    inputs: [{ id: 'input', label: 'Input', type: 'input', dataType: 'any' }],
    outputs: [{ id: 'valid', label: 'Valid', type: 'output', dataType: 'boolean' }],
  },
};

// =============================================================================
// Enhanced Node Component
// =============================================================================

const EnhancedWorkflowNode: React.FC<{
  data: WorkflowNodeData;
  selected: boolean;
}> = ({ data, selected }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  
  const statusStyles = {
    idle: 'border-gray-300 bg-white',
    running: 'border-blue-500 bg-blue-50 animate-pulse',
    completed: 'border-green-500 bg-green-50',
    failed: 'border-red-500 bg-red-50',
    paused: 'border-yellow-500 bg-yellow-50',
  };

  const categoryStyles = {
    control: 'border-l-purple-500',
    ai: 'border-l-blue-500',
    integration: 'border-l-green-500',
    processing: 'border-l-orange-500',
    io: 'border-l-gray-500',
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      className={cn(
        'relative rounded-lg border-2 border-l-4 shadow-lg transition-all duration-200 min-w-[200px]',
        statusStyles[data.status],
        categoryStyles[data.category],
        selected && 'ring-2 ring-blue-400 ring-offset-2'
      )}
    >
      {/* Node Header */}
      <div className="flex items-center justify-between p-3 border-b">
        <div className="flex items-center space-x-2">
          {data.icon}
          <span className="font-medium text-sm">{data.label}</span>
        </div>
        <div className="flex items-center space-x-1">
          <Badge variant="outline" className="text-xs">
            {data.type}
          </Badge>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
            className="h-6 w-6 p-0"
          >
            {isExpanded ? <Minimize2 className="h-3 w-3" /> : <Maximize2 className="h-3 w-3" />}
          </Button>
        </div>
      </div>

      {/* Node Body */}
      <div className="p-3">
        <p className="text-xs text-gray-600 mb-2">{data.description}</p>
        
        {/* Status Indicator */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-1">
            {data.status === 'running' && <Loader2 className="h-3 w-3 animate-spin" />}
            {data.status === 'completed' && <CheckCircle className="h-3 w-3 text-green-500" />}
            {data.status === 'failed' && <XCircle className="h-3 w-3 text-red-500" />}
            <span className="text-xs capitalize">{data.status}</span>
          </div>
          {data.metrics && (
            <span className="text-xs text-gray-500">
              {data.metrics.executionTime}ms
            </span>
          )}
        </div>

        {/* Expanded Details */}
        <AnimatePresence>
          {isExpanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="border-t pt-2 mt-2"
            >
              {/* Configuration Preview */}
              {data.config && Object.keys(data.config).length > 0 && (
                <div className="mb-2">
                  <div className="text-xs font-medium mb-1">Config:</div>
                  <div className="text-xs bg-gray-100 p-1 rounded">
                    {JSON.stringify(data.config, null, 2).substring(0, 100)}...
                  </div>
                </div>
              )}

              {/* Validation Results */}
              {data.validation && (
                <div className="mb-2">
                  <div className="text-xs font-medium mb-1">Validation:</div>
                  <div className="space-y-1">
                    {data.validation.errors.map((error, idx) => (
                      <div key={idx} className="text-xs text-red-600 flex items-center">
                        <XCircle className="h-3 w-3 mr-1" />
                        {error}
                      </div>
                    ))}
                    {data.validation.warnings.map((warning, idx) => (
                      <div key={idx} className="text-xs text-yellow-600 flex items-center">
                        <AlertCircle className="h-3 w-3 mr-1" />
                        {warning}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Input Handles */}
      {data.inputs?.map((input, idx) => (
        <Handle
          key={input.id}
          type="target"
          position={Position.Left}
          id={input.id}
          style={{ top: `${50 + idx * 20}%` }}
          className="!bg-blue-500 !w-3 !h-3"
        />
      ))}

      {/* Output Handles */}
      {data.outputs?.map((output, idx) => (
        <Handle
          key={output.id}
          type="source"
          position={Position.Right}
          id={output.id}
          style={{ top: `${50 + idx * 20}%` }}
          className="!bg-green-500 !w-3 !h-3"
        />
      ))}
    </motion.div>
  );
};

// =============================================================================
// Node Palette Component
// =============================================================================

const NodePalette: React.FC<{
  onAddNode: (nodeType: NodeType) => void;
  isVisible: boolean;
}> = ({ onAddNode, isVisible }) => {
  const [selectedCategory, setSelectedCategory] = useState<NodeCategory>('control');
  
  const categories = {
    control: 'Control Flow',
    ai: 'AI & ML',
    integration: 'Integration',
    processing: 'Processing',
    io: 'Input/Output',
  };

  const getNodesByCategory = (category: NodeCategory) => {
    return Object.entries(NODE_TEMPLATES).filter(
      ([_, template]) => template.category === category
    );
  };

  if (!isVisible) return null;

  return (
    <motion.div
      initial={{ x: -300, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: -300, opacity: 0 }}
      className="w-72 bg-white border-r p-4 overflow-y-auto"
    >
      <div className="mb-4">
        <h3 className="font-semibold mb-2">Node Library</h3>
        <Select value={selectedCategory} onValueChange={(val) => setSelectedCategory(val as NodeCategory)}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {Object.entries(categories).map(([key, label]) => (
              <SelectItem key={key} value={key}>
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        {getNodesByCategory(selectedCategory).map(([nodeType, template]) => (
          <Card
            key={nodeType}
            className="cursor-pointer hover:bg-gray-50 transition-colors"
            onClick={() => onAddNode(nodeType as NodeType)}
          >
            <CardContent className="p-3">
              <div className="flex items-center space-x-2 mb-1">
                {template.icon}
                <span className="font-medium text-sm">{template.label}</span>
              </div>
              <p className="text-xs text-gray-600">{template.description}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </motion.div>
  );
};

// =============================================================================
// Properties Panel Component
// =============================================================================

const PropertiesPanel: React.FC<{
  selectedNode: Node<WorkflowNodeData> | null;
  onUpdateNode: (nodeId: string, updates: Partial<WorkflowNodeData>) => void;
  isVisible: boolean;
}> = ({ selectedNode, onUpdateNode, isVisible }) => {
  if (!isVisible || !selectedNode) return null;

  const handleConfigChange = (key: string, value: any) => {
    onUpdateNode(selectedNode.id, {
      config: { ...selectedNode.data.config, [key]: value }
    });
  };

  const handleBasicChange = (key: keyof WorkflowNodeData, value: any) => {
    onUpdateNode(selectedNode.id, { [key]: value });
  };

  return (
    <motion.div
      initial={{ x: 300, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 300, opacity: 0 }}
      className="w-80 bg-white border-l p-4 overflow-y-auto"
    >
      <div className="mb-4">
        <h3 className="font-semibold mb-2">Node Properties</h3>
        <div className="flex items-center space-x-2 mb-2">
          {selectedNode.data.icon}
          <span className="font-medium">{selectedNode.data.label}</span>
        </div>
      </div>

      <Tabs defaultValue="general" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="general">General</TabsTrigger>
          <TabsTrigger value="config">Config</TabsTrigger>
          <TabsTrigger value="validation">Validation</TabsTrigger>
        </TabsList>

        <TabsContent value="general" className="space-y-4">
          <div>
            <label className="text-sm font-medium">Label</label>
            <Input
              value={selectedNode.data.label}
              onChange={(e) => handleBasicChange('label', e.target.value)}
            />
          </div>
          <div>
            <label className="text-sm font-medium">Description</label>
            <Textarea
              value={selectedNode.data.description}
              onChange={(e) => handleBasicChange('description', e.target.value)}
              rows={3}
            />
          </div>
          <div>
            <label className="text-sm font-medium">Status</label>
            <Select
              value={selectedNode.data.status}
              onValueChange={(val) => handleBasicChange('status', val)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="idle">Idle</SelectItem>
                <SelectItem value="running">Running</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
                <SelectItem value="paused">Paused</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </TabsContent>

        <TabsContent value="config" className="space-y-4">
          {/* Dynamic configuration based on node type */}
          {selectedNode.data.type === 'llm' && (
            <>
              <div>
                <label className="text-sm font-medium">Provider</label>
                <Select
                  value={selectedNode.data.config.provider}
                  onValueChange={(val) => handleConfigChange('provider', val)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="openai">OpenAI</SelectItem>
                    <SelectItem value="anthropic">Anthropic</SelectItem>
                    <SelectItem value="local">Local</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-sm font-medium">Model</label>
                <Input
                  value={selectedNode.data.config.model}
                  onChange={(e) => handleConfigChange('model', e.target.value)}
                />
              </div>
              <div>
                <label className="text-sm font-medium">Temperature</label>
                <Input
                  type="number"
                  step="0.1"
                  min="0"
                  max="2"
                  value={selectedNode.data.config.temperature}
                  onChange={(e) => handleConfigChange('temperature', parseFloat(e.target.value))}
                />
              </div>
              <div>
                <label className="text-sm font-medium">Prompt Template</label>
                <Textarea
                  value={selectedNode.data.config.promptTemplate || ''}
                  onChange={(e) => handleConfigChange('promptTemplate', e.target.value)}
                  rows={6}
                />
              </div>
            </>
          )}

          {selectedNode.data.type === 'delay' && (
            <div>
              <label className="text-sm font-medium">Duration (seconds)</label>
              <Input
                type="number"
                value={selectedNode.data.config.duration || 1}
                onChange={(e) => handleConfigChange('duration', parseInt(e.target.value))}
              />
            </div>
          )}

          {selectedNode.data.type === 'api' && (
            <>
              <div>
                <label className="text-sm font-medium">URL</label>
                <Input
                  value={selectedNode.data.config.url || ''}
                  onChange={(e) => handleConfigChange('url', e.target.value)}
                />
              </div>
              <div>
                <label className="text-sm font-medium">Method</label>
                <Select
                  value={selectedNode.data.config.method || 'GET'}
                  onValueChange={(val) => handleConfigChange('method', val)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="GET">GET</SelectItem>
                    <SelectItem value="POST">POST</SelectItem>
                    <SelectItem value="PUT">PUT</SelectItem>
                    <SelectItem value="DELETE">DELETE</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-sm font-medium">Headers</label>
                <Textarea
                  value={selectedNode.data.config.headers || ''}
                  onChange={(e) => handleConfigChange('headers', e.target.value)}
                  rows={3}
                  placeholder="JSON format"
                />
              </div>
            </>
          )}

          {/* Generic config for other node types */}
          {!['llm', 'delay', 'api'].includes(selectedNode.data.type) && (
            <div>
              <label className="text-sm font-medium">Configuration</label>
              <Textarea
                value={JSON.stringify(selectedNode.data.config, null, 2)}
                onChange={(e) => {
                  try {
                    const config = JSON.parse(e.target.value);
                    handleBasicChange('config', config);
                  } catch (error) {
                    // Invalid JSON, ignore
                  }
                }}
                rows={8}
                placeholder="JSON configuration"
              />
            </div>
          )}
        </TabsContent>

        <TabsContent value="validation" className="space-y-4">
          {selectedNode.data.validation ? (
            <div>
              <div className="mb-2">
                <Badge variant={selectedNode.data.validation.isValid ? "default" : "destructive"}>
                  {selectedNode.data.validation.isValid ? "Valid" : "Invalid"}
                </Badge>
              </div>
              
              {selectedNode.data.validation.errors.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-red-600 mb-1">Errors:</h4>
                  <ul className="text-sm text-red-600 space-y-1">
                    {selectedNode.data.validation.errors.map((error, idx) => (
                      <li key={idx} className="flex items-center">
                        <XCircle className="h-3 w-3 mr-1" />
                        {error}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {selectedNode.data.validation.warnings.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-yellow-600 mb-1">Warnings:</h4>
                  <ul className="text-sm text-yellow-600 space-y-1">
                    {selectedNode.data.validation.warnings.map((warning, idx) => (
                      <li key={idx} className="flex items-center">
                        <AlertCircle className="h-3 w-3 mr-1" />
                        {warning}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-gray-500">No validation results available</p>
          )}

          <Button
            onClick={() => {
              // Simulate validation
              const errors = [];
              const warnings = [];
              
              if (!selectedNode.data.label.trim()) {
                errors.push("Label is required");
              }
              
              if (selectedNode.data.type === 'llm' && !selectedNode.data.config.model) {
                errors.push("Model is required for LLM nodes");
              }
              
              if (selectedNode.data.type === 'api' && !selectedNode.data.config.url) {
                errors.push("URL is required for API nodes");
              }
              
              if (selectedNode.data.inputs?.length === 0 && selectedNode.data.type !== 'start') {
                warnings.push("Node has no inputs");
              }
              
              const validation: ValidationResult = {
                isValid: errors.length === 0,
                errors,
                warnings,
              };
              
              onUpdateNode(selectedNode.id, { validation });
            }}
            className="w-full"
          >
            Validate Node
          </Button>
        </TabsContent>
      </Tabs>
    </motion.div>
  );
};

// =============================================================================
// Main Advanced Workflow Editor Component
// =============================================================================

export const AdvancedWorkflowEditor: React.FC<{
  workflowId?: string;
  initialNodes?: Node<WorkflowNodeData>[];
  initialEdges?: Edge[];
  onSave?: (nodes: Node<WorkflowNodeData>[], edges: Edge[]) => void;
}> = ({ workflowId, initialNodes = [], initialEdges = [], onSave }) => {
  const [nodes, setNodes, onNodesChange] = useNodesState<WorkflowNodeData>(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selectedNode, setSelectedNode] = useState<Node<WorkflowNodeData> | null>(null);
  const [showNodePalette, setShowNodePalette] = useState(true);
  const [showPropertiesPanel, setShowPropertiesPanel] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const queryClient = useQueryClient();

  const nodeTypes: NodeTypes = useMemo(() => ({
    workflowNode: EnhancedWorkflowNode,
  }), []);

  const saveMutation = useMutation({
    mutationFn: (data: { nodes: Node<WorkflowNodeData>[], edges: Edge[] }) => {
      if (workflowId) {
        return apiClient.updateWorkflow(workflowId, data);
      }
      return Promise.resolve(data);
    },
    onSuccess: () => {
      toast({
        title: "Success",
        description: "Workflow saved successfully",
      });
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: "Failed to save workflow",
        variant: "destructive",
      });
    },
  });

  const handleSave = () => {
    if (onSave) {
      onSave(nodes, edges);
    } else {
      saveMutation.mutate({ nodes, edges });
    }
  };

  const handleAddNode = (nodeType: NodeType) => {
    const template = NODE_TEMPLATES[nodeType];
    if (!template) return;

    const newNode: Node<WorkflowNodeData> = {
      id: uuidv4(),
      type: 'workflowNode',
      position: { x: 250, y: 100 + nodes.length * 100 },
      data: {
        ...template,
        id: uuidv4(),
        type: nodeType,
        status: 'idle',
        config: template.config || {},
        inputs: template.inputs || [],
        outputs: template.outputs || [],
      } as WorkflowNodeData,
    };

    setNodes((nds) => [...nds, newNode]);
  };

  const handleUpdateNode = (nodeId: string, updates: Partial<WorkflowNodeData>) => {
    setNodes((nds) =>
      nds.map((node) =>
        node.id === nodeId
          ? { ...node, data: { ...node.data, ...updates } }
          : node
      )
    );
  };

  const onConnect = useCallback(
    (params: Connection) => {
      const newEdge: Edge = {
        ...params,
        type: 'smoothstep',
        animated: true,
        style: { stroke: '#3b82f6', strokeWidth: 2 },
      };
      setEdges((eds) => addEdge(newEdge, eds));
    },
    [setEdges]
  );

  const onNodeClick = useCallback((_, node: Node<WorkflowNodeData>) => {
    setSelectedNode(node);
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  const executeWorkflow = async () => {
    toast({
      title: "Executing Workflow",
      description: "Starting workflow execution...",
    });

    // Simulate workflow execution
    for (const node of nodes) {
      if (node.data.type === 'start') continue;
      
      setNodes((nds) =>
        nds.map((n) =>
          n.id === node.id
            ? { ...n, data: { ...n.data, status: 'running' } }
            : n
        )
      );

      await new Promise(resolve => setTimeout(resolve, 1000));

      setNodes((nds) =>
        nds.map((n) =>
          n.id === node.id
            ? { 
                ...n, 
                data: { 
                  ...n.data, 
                  status: 'completed',
                  metrics: {
                    ...n.data.metrics,
                    executionTime: Math.random() * 1000,
                    lastRun: new Date().toISOString(),
                  }
                }
              }
            : n
        )
      );
    }

    toast({
      title: "Workflow Completed",
      description: "All nodes executed successfully",
    });
  };

  return (
    <div className={cn("flex flex-col h-screen bg-gray-50", isFullscreen && "fixed inset-0 z-50")}>
      {/* Toolbar */}
      <div className="flex items-center justify-between p-4 bg-white border-b">
        <div className="flex items-center space-x-2">
          <h1 className="text-xl font-bold">Advanced Workflow Editor</h1>
          <Badge variant="outline">Beta</Badge>
        </div>
        
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowNodePalette(!showNodePalette)}
          >
            <Grid className="h-4 w-4 mr-2" />
            {showNodePalette ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </Button>
          
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowPropertiesPanel(!showPropertiesPanel)}
          >
            <Settings className="h-4 w-4 mr-2" />
            {showPropertiesPanel ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </Button>
          
          <Button variant="outline" size="sm" onClick={executeWorkflow}>
            <Play className="h-4 w-4 mr-2" />
            Execute
          </Button>
          
          <Button variant="outline" size="sm" onClick={handleSave} disabled={saveMutation.isPending}>
            {saveMutation.isPending ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Save className="h-4 w-4 mr-2" />
            )}
            Save
          </Button>
          
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsFullscreen(!isFullscreen)}
          >
            {isFullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
          </Button>
        </div>
      </div>

      {/* Main Editor */}
      <div className="flex flex-1 overflow-hidden">
        <AnimatePresence>
          {showNodePalette && (
            <NodePalette onAddNode={handleAddNode} isVisible={showNodePalette} />
          )}
        </AnimatePresence>

        <ReactFlowProvider>
          <div className="flex-1 relative">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              onNodeClick={onNodeClick}
              onPaneClick={onPaneClick}
              nodeTypes={nodeTypes}
              connectionLineType={ConnectionLineType.SmoothStep}
              fitView
              attributionPosition="bottom-left"
            >
              <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
              <Controls />
              <MiniMap />
            </ReactFlow>
          </div>
        </ReactFlowProvider>

        <AnimatePresence>
          {showPropertiesPanel && (
            <PropertiesPanel
              selectedNode={selectedNode}
              onUpdateNode={handleUpdateNode}
              isVisible={showPropertiesPanel}
            />
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default AdvancedWorkflowEditor;