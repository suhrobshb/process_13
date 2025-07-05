import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
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
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
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
} from 'lucide-react';
import { v4 as uuidv4 } from 'uuid';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/components/ui/use-toast';
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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
} from "@/components/ui/dropdown-menu";
import { apiClient, Workflow } from '@/lib/api-client';

// --- Enhanced Type Definitions ---

type NodeType = 'system' | 'communication' | 'decision' | 'llm';

type BaseNodeData = {
  label: string;
  type: NodeType;
  icon: React.ReactNode;
  confidence: number;
  status: 'pending' | 'running' | 'completed' | 'failed' | null;
  process: { description: string };
};

type LLMNodeData = BaseNodeData & {
  type: 'llm';
  llm: {
    provider: 'openai' | 'anthropic' | 'local';
    model: string;
    promptTemplate: string;
    outputSchema?: string; // JSON schema as a string
  };
};

type DecisionNodeData = BaseNodeData & {
    type: 'decision';
    scenarios: { id: string; label: string }[];
};

type GenericNodeData = BaseNodeData & {
    type: 'system' | 'communication';
};

type NodeData = LLMNodeData | DecisionNodeData | GenericNodeData;

// --- Custom Node Component ---
const ActionStepNode = ({ data, selected }: { data: NodeData; selected: boolean }) => {
  const nodeTypeStyles = {
    system: 'border-purple-500 bg-purple-50',
    communication: 'border-green-500 bg-green-50',
    decision: 'border-yellow-500 bg-yellow-50',
    llm: 'border-blue-500 bg-blue-50',
  };

  const statusStyles = {
    running: 'ring-2 ring-blue-500 ring-offset-2 animate-pulse',
    completed: 'opacity-70',
    failed: 'ring-2 ring-red-500 ring-offset-2',
  };

  return (
    <div
      className={cn(
        'w-96 rounded-lg bg-white shadow-lg transition-all border-2',
        nodeTypeStyles[data.type],
        selected && 'ring-2 ring-blue-600 shadow-xl',
        statusStyles[data.status]
      )}
    >
      <div className={cn("p-3 rounded-t-lg flex items-center gap-3 border-b-2", nodeTypeStyles[data.type])}>
        <div className="flex-shrink-0">{data.icon}</div>
        <h3 className="font-bold flex-grow">{data.label}</h3>
        <Badge variant="secondary">{`${Math.round(data.confidence * 100)}%`}</Badge>
      </div>

      <div className="p-3 space-y-2 text-sm">
        <p className="text-gray-600">{data.process.description}</p>
        {data.type === 'llm' && (
          <div className="mt-2 p-2 bg-gray-800 text-gray-200 rounded font-mono text-xs overflow-x-auto">
            <pre className="whitespace-pre-wrap"><code>{data.llm.promptTemplate}</code></pre>
          </div>
        )}
      </div>

      <Handle type="target" position={Position.Left} className="!bg-gray-500 !w-3 !h-3" />
      {data.type === 'decision' ? (
        data.scenarios.map((scenario, index) => (
          <div key={scenario.id} className="relative">
             <Handle
                type="source"
                position={Position.Right}
                id={scenario.id}
                style={{ top: `${(100 / (data.scenarios.length + 1)) * (index + 1)}%` }}
                className="!bg-yellow-500 !w-3 !h-3"
            />
            <div className="absolute right-[-80px] text-xs text-gray-500" style={{ top: `${(100 / (data.scenarios.length + 1)) * (index + 1) - 2}%` }}>
                {scenario.label}
            </div>
          </div>
        ))
      ) : (
        <Handle type="source" position={Position.Right} className="!bg-gray-500 !w-3 !h-3" />
      )}
    </div>
  );
};

const nodeTypes = { actionStep: ActionStepNode };

// --- Properties Panel Components ---
const LLMConfigPanel = ({ nodeData, updateNodeData }) => {
    const { toast } = useToast();
    const [testOutput, setTestOutput] = useState('');
    const availableVariables = ["{{ step1.output.data }}", "{{ step2.output.summary }}"];

    const testPromptMutation = useMutation({
        mutationFn: apiClient.executeLLMStep,
        onSuccess: (data) => {
            toast({ title: "Prompt Test Successful" });
            setTestOutput(JSON.stringify(data.result, null, 2));
        },
        onError: (error: Error) => {
            toast({ title: "Prompt Test Failed", description: error.message, variant: "destructive" });
            setTestOutput(`Error: ${error.message}`);
        },
    });

    const handleTestPrompt = () => {
        setTestOutput('');
        testPromptMutation.mutate({
            provider: nodeData.llm.provider,
            model: nodeData.llm.model,
            prompt_template: nodeData.llm.promptTemplate,
            context: {}, // Using empty context for now
        });
    };

    const handleInsertVariable = (variable: string) => {
        const currentPrompt = nodeData.llm.promptTemplate || "";
        updateNodeData('llm', { ...nodeData.llm, promptTemplate: currentPrompt + variable });
    };

    return (
        <div className="space-y-4">
            <div>
                <label className="text-sm font-medium">LLM Provider</label>
                <Select value={nodeData.llm.provider} onValueChange={(v) => updateNodeData('llm', { ...nodeData.llm, provider: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                        <SelectItem value="openai">OpenAI</SelectItem>
                        <SelectItem value="anthropic">Anthropic</SelectItem>
                        <SelectItem value="local">Local Model</SelectItem>
                    </SelectContent>
                </Select>
            </div>
            <div>
                <label className="text-sm font-medium">Model</label>
                <Input value={nodeData.llm.model} onChange={e => updateNodeData('llm', { ...nodeData.llm, model: e.target.value })} placeholder="e.g., gpt-4-turbo" />
            </div>
            <div>
                <label className="text-sm font-medium">Prompt Template</label>
                <Textarea value={nodeData.llm.promptTemplate} onChange={e => updateNodeData('llm', { ...nodeData.llm, promptTemplate: e.target.value })} rows={8} />
                <div className="mt-2 flex items-center gap-2">
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button variant="outline" size="sm">Insert Variable <ChevronDown className="ml-2 h-4 w-4" /></Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent>
                            {availableVariables.map(v => <DropdownMenuItem key={v} onClick={() => handleInsertVariable(v)}>{v}</DropdownMenuItem>)}
                        </DropdownMenuContent>
                    </DropdownMenu>
                    <Button variant="secondary" size="sm" onClick={handleTestPrompt} disabled={testPromptMutation.isPending}>
                        {testPromptMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Code2 className="mr-2 h-4 w-4" />}
                        Test Prompt
                    </Button>
                </div>
            </div>
            {testPromptMutation.isPending && <div className="text-sm text-muted-foreground">Testing prompt...</div>}
            {testOutput && (
                <div>
                    <label className="text-sm font-medium">Test Output</label>
                    <pre className="mt-2 p-2 bg-gray-800 text-gray-200 rounded font-mono text-xs max-h-40 overflow-y-auto">{testOutput}</pre>
                </div>
            )}
            <div>
                <label className="text-sm font-medium">Output JSON Schema (Optional)</label>
                <Textarea value={nodeData.llm.outputSchema || ''} onChange={e => updateNodeData('llm', { ...nodeData.llm, outputSchema: e.target.value })} rows={6} placeholder={`{ "type": "object", "properties": { ... } }`} />
            </div>
        </div>
    );
};

const PropertiesPanel = ({ selectedNode, updateNodeData }) => {
    if (!selectedNode) {
        return <div className="p-4 text-center text-gray-500">Select a node to edit its properties.</div>;
    }

    const handleDataChange = (field, value) => {
        updateNodeData(selectedNode.id, { ...selectedNode.data, [field]: value });
    };
    
    const handleProcessChange = (field, value) => {
        updateNodeData(selectedNode.id, { ...selectedNode.data, process: { ...selectedNode.data.process, [field]: value } });
    };

    const handleLlmChange = (subfield, value) => {
        updateNodeData(selectedNode.id, { ...selectedNode.data, llm: { ...selectedNode.data.llm, [subfield]: value } });
    };

    return (
        <aside className="w-96 bg-white border-l p-4 overflow-y-auto">
            <h2 className="text-lg font-bold mb-4">Edit: {selectedNode.data.label}</h2>
            <div className="space-y-4">
                <div>
                    <label className="text-sm font-medium">Action Title</label>
                    <Input value={selectedNode.data.label} onChange={e => handleDataChange('label', e.target.value)} />
                </div>
                <div>
                    <label className="text-sm font-medium">AI-Generated Description</label>
                    <Textarea value={selectedNode.data.process.description} onChange={e => handleProcessChange('description', e.target.value)} rows={5} />
                </div>
                {selectedNode.data.type === 'llm' && (
                    <LLMConfigPanel nodeData={selectedNode.data} updateNodeData={handleDataChange} />
                )}
            </div>
        </aside>
    );
};


// --- Main Editor Component ---
export default function VisualWorkflowEditor({ workflowId }: { workflowId: number }) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const importInputRef = useRef<HTMLInputElement>(null);

  const { data: workflow, isLoading, isError } = useQuery<Workflow, Error>({
      queryKey: ['workflow', workflowId],
      queryFn: () => apiClient.getWorkflow(workflowId),
      enabled: !!workflowId,
  });

  useEffect(() => {
    if (workflow) {
      setNodes(workflow.nodes || []);
      setEdges(workflow.edges || []);
    }
  }, [workflow, setNodes, setEdges]);
  
  const saveMutation = useMutation({
    mutationFn: (workflowData: Partial<Workflow>) => apiClient.updateWorkflow(workflowId, workflowData),
    onSuccess: () => {
        toast({ title: "Workflow Saved", description: "Your changes have been saved successfully." });
        queryClient.invalidateQueries({ queryKey: ['workflow', workflowId] });
        queryClient.invalidateQueries({ queryKey: ['workflows'] });
    },
    onError: (error: Error) => {
        toast({ title: "Save Failed", description: error.message, variant: "destructive" });
    }
  });

  const handleSave = () => {
    saveMutation.mutate({ nodes, edges });
  };

  const onConnect = useCallback((params) => setEdges((eds) => addEdge({ ...params, type: ConnectionLineType.SmoothStep, animated: true }, eds)), [setEdges]);
  const onNodeClick = useCallback((_, node) => setSelectedNode(node), []);
  const onPaneClick = useCallback(() => setSelectedNode(null), []);

  const updateNodeData = (nodeId, newData) => {
    setNodes(nds => nds.map(n => n.id === nodeId ? { ...n, data: newData } : n));
    if (selectedNode && selectedNode.id === nodeId) {
        setSelectedNode(prev => ({ ...prev, data: newData }));
    }
  };

  const addNode = (nodeType: NodeType) => {
    const id = uuidv4();
    const position = { x: 250, y: 100 + nodes.length * 50 };
    const iconMap = {
      system: <Cpu className="h-6 w-6 text-purple-600" />,
      communication: <Mail className="h-6 w-6 text-green-600" />,
      decision: <GitBranch className="h-6 w-6 text-yellow-600" />,
      llm: <Bot className="h-6 w-6 text-blue-600" />,
    };
    
    let newNodeData: NodeData;
    const baseData = {
        label: `New ${nodeType} Step`,
        type: nodeType,
        icon: iconMap[nodeType],
        confidence: 0.8,
        status: null,
        process: { description: `A new step of type ${nodeType}` },
    };

    if (nodeType === 'llm') {
        newNodeData = { ...baseData, type: 'llm', llm: { provider: 'openai', model: 'gpt-4-turbo', promptTemplate: 'Your prompt here...' } };
    } else if (nodeType === 'decision') {
        newNodeData = { ...baseData, type: 'decision', scenarios: [{id: 'true', label: 'True'}, {id: 'false', label: 'False'}] };
    } else {
        newNodeData = { ...baseData, type: nodeType };
    }

    const newNode = { id, type: 'actionStep', position, data: newNodeData };
    setNodes(nds => nds.concat(newNode));
  };

  if (isLoading) return <div className="flex justify-center items-center h-full"><Loader2 className="h-8 w-8 animate-spin" /></div>;
  if (isError) return <div className="p-4"><Alert variant="destructive"><AlertCircle className="h-4 w-4" /><AlertTitle>Error</AlertTitle><AlertDescription>Failed to load workflow.</AlertDescription></Alert></div>;

  return (
    <div className="h-screen w-screen flex flex-col bg-gray-100">
      <header className="p-3 border-b bg-white flex justify-between items-center z-10">
        <h1 className="text-xl font-bold">{workflow?.name || "Workflow Editor"}</h1>
        <div className="flex items-center gap-2">
            <DropdownMenu>
                <DropdownMenuTrigger asChild>
                    <Button>+ Add Node <ChevronDown className="ml-2 h-4 w-4" /></Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                    <DropdownMenuItem onClick={() => addNode('llm')}><Bot className="mr-2 h-4 w-4" />LLM</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => addNode('decision')}><GitBranch className="mr-2 h-4 w-4" />Decision</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => addNode('communication')}><Mail className="mr-2 h-4 w-4" />Communication</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => addNode('system')}><Cpu className="mr-2 h-4 w-4" />System</DropdownMenuItem>
                </DropdownMenuContent>
            </DropdownMenu>
            <Button variant="outline" onClick={handleSave} disabled={saveMutation.isPending}>
                {saveMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                Save
            </Button>
            <Button variant="outline" onClick={() => { /* export */ }}><Download className="mr-2 h-4 w-4" />Export</Button>
            <Button variant="outline" onClick={() => importInputRef.current?.click()}><Upload className="mr-2 h-4 w-4" />Import</Button>
            <input ref={importInputRef} type="file" className="hidden" />
            <Button variant="destructive" onClick={() => { setNodes([]); setEdges([]); }}><Trash2 className="mr-2 h-4 w-4" />Clear</Button>
        </div>
      </header>
      <div className="flex flex-grow overflow-hidden">
        <ReactFlowProvider>
          <div className="flex-grow h-full">
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
            >
              <Background />
              <Controls />
              <MiniMap />
            </ReactFlow>
          </div>
          <PropertiesPanel selectedNode={selectedNode} updateNodeData={updateNodeData} />
        </ReactFlowProvider>
      </div>
    </div>
  );
}
