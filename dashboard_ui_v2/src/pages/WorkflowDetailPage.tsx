import React, { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Loader2, Save, Play, AlertCircle } from "lucide-react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { apiClient, Workflow, Execution } from "@/lib/api-client";
import VisualWorkflowEditor from "@/components/workflow-editor/VisualWorkflowEditor";
import { useToast } from "@/components/ui/use-toast";
import { formatDate, capitalize } from "@/lib/utils";

// --- Zod Schema for Settings Form Validation ---
const settingsSchema = z.object({
  name: z.string().min(3, "Workflow name must be at least 3 characters long."),
  description: z.string().optional(),
  status: z.enum(["draft", "active", "archived"]),
});

type SettingsFormData = z.infer<typeof settingsSchema>;

// --- API Functions for TanStack Query ---
const fetchWorkflowDetails = async (id: string): Promise<Workflow> => {
  if (id === 'new') {
    // Return a default new workflow structure
    return {
      id: null,
      name: 'New Untitled Workflow',
      description: 'A new workflow ready for configuration.',
      status: 'draft',
      nodes: [],
      edges: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
  }
  return apiClient.getWorkflow(parseInt(id, 10));
};

const fetchWorkflowExecutions = async (id: string): Promise<Execution[]> => {
    if (id === 'new') return [];
    return apiClient.getExecutions(parseInt(id, 10));
};

// --- Main Workflow Detail Page Component ---
export default function WorkflowDetailPage({ id }: { id: string }) {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const { data: workflow, isLoading, isError, error } = useQuery<Workflow, Error>({
    queryKey: ["workflow", id],
    queryFn: () => fetchWorkflowDetails(id),
    enabled: !!id, // Only run query if ID is available
  });
  
  const { data: executions, isLoading: isLoadingExecutions } = useQuery<Execution[], Error>({
    queryKey: ["executions", id],
    queryFn: () => fetchWorkflowExecutions(id),
    enabled: !!id && id !== 'new',
  });

  // State for the editor's nodes and edges
  const [editorNodes, setEditorNodes] = useState(workflow?.nodes || []);
  const [editorEdges, setEditorEdges] = useState(workflow?.edges || []);

  useEffect(() => {
    if (workflow) {
      setEditorNodes(workflow.nodes);
      setEditorEdges(workflow.edges);
    }
  }, [workflow]);

  // Form handling for settings tab
  const {
    control,
    handleSubmit,
    reset,
    formState: { isDirty, errors },
  } = useForm<SettingsFormData>({
    resolver: zodResolver(settingsSchema),
    defaultValues: {
      name: "",
      description: "",
      status: "draft",
    },
  });

  useEffect(() => {
    if (workflow) {
      reset({
        name: workflow.name,
        description: workflow.description || "",
        status: workflow.status as any,
      });
    }
  }, [workflow, reset]);

  // Mutation for updating/creating the workflow
  const saveMutation = useMutation({
    mutationFn: (data: Partial<Workflow>) => {
        const payload = { ...data, nodes: editorNodes, edges: editorEdges };
        return id === 'new'
            ? apiClient.createWorkflow(payload)
            : apiClient.updateWorkflow(parseInt(id, 10), payload);
    },
    onSuccess: (savedWorkflow) => {
      toast({ title: "Success", description: "Workflow saved successfully." });
      queryClient.invalidateQueries({ queryKey: ["workflows"] });
      queryClient.setQueryData(["workflow", id], savedWorkflow);
      if (id === 'new') {
        // Redirect to the new workflow's page
        window.history.replaceState(null, '', `/workflows/${savedWorkflow.id}`);
      }
    },
    onError: (err: Error) => {
      toast({
        title: "Error",
        description: `Failed to save workflow: ${err.message}`,
        variant: "destructive",
      });
    },
  });

  const onSaveSettings = (data: SettingsFormData) => {
    saveMutation.mutate(data);
  };
  
  const onSaveEditor = () => {
    saveMutation.mutate({}); // Save with current nodes/edges
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="ml-4 text-lg">Loading Workflow...</span>
      </div>
    );
  }

  if (isError) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>
          Failed to load workflow: {error.message}
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-4 h-full flex flex-col">
      <div className="flex items-center justify-between">
        <div>
            <h1 className="text-3xl font-bold tracking-tight">{workflow?.name}</h1>
            <p className="text-muted-foreground">{workflow?.description}</p>
        </div>
        <div className="flex items-center space-x-2">
            <Button onClick={onSaveEditor} disabled={saveMutation.isPending}>
                <Save className="mr-2 h-4 w-4" />
                {saveMutation.isPending ? 'Saving...' : 'Save Workflow'}
            </Button>
            <Button variant="secondary" disabled={id === 'new'}>
                <Play className="mr-2 h-4 w-4" />
                Run Workflow
            </Button>
        </div>
      </div>

      <Tabs defaultValue="editor" className="flex-grow flex flex-col">
        <TabsList>
          <TabsTrigger value="editor">Editor</TabsTrigger>
          <TabsTrigger value="executions" disabled={id === 'new'}>Executions</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
        </TabsList>

        <TabsContent value="editor" className="flex-grow mt-4 h-full">
          <VisualWorkflowEditor
            initialNodes={editorNodes}
            initialEdges={editorEdges}
            onNodesChange={setEditorNodes}
            onEdgesChange={setEditorEdges}
          />
        </TabsContent>

        <TabsContent value="executions" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Execution History</CardTitle>
              <CardDescription>
                A log of all runs for this workflow.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Execution ID</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Started At</TableHead>
                    <TableHead>Duration</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {isLoadingExecutions ? (
                    <TableRow><TableCell colSpan={4} className="text-center">Loading...</TableCell></TableRow>
                  ) : executions && executions.length > 0 ? (
                    executions.map((exec) => (
                      <TableRow key={exec.id}>
                        <TableCell>{exec.id}</TableCell>
                        <TableCell><Badge>{capitalize(exec.status)}</Badge></TableCell>
                        <TableCell>{formatDate(exec.started_at, "PPpp")}</TableCell>
                        <TableCell>{exec.completed_at ? `${((new Date(exec.completed_at).getTime() - new Date(exec.started_at).getTime()) / 1000).toFixed(2)}s` : 'N/A'}</TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow><TableCell colSpan={4} className="text-center">No executions found.</TableCell></TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="settings" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Workflow Settings</CardTitle>
              <CardDescription>
                Manage the name, description, and status of your workflow.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit(onSaveSettings)} className="space-y-6">
                <div className="space-y-2">
                  <label htmlFor="name">Workflow Name</label>
                  <Controller
                    name="name"
                    control={control}
                    render={({ field }) => <Input id="name" {...field} />}
                  />
                  {errors.name && <p className="text-red-500 text-sm">{errors.name.message}</p>}
                </div>
                <div className="space-y-2">
                  <label htmlFor="description">Description</label>
                  <Controller
                    name="description"
                    control={control}
                    render={({ field }) => <Textarea id="description" {...field} />}
                  />
                </div>
                <div className="space-y-2">
                  <label htmlFor="status">Status</label>
                  <Controller
                    name="status"
                    control={control}
                    render={({ field }) => (
                      <Select onValueChange={field.onChange} value={field.value}>
                        <SelectTrigger id="status">
                          <SelectValue placeholder="Select status" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="draft">Draft</SelectItem>
                          <SelectItem value="active">Active</SelectItem>
                          <SelectItem value="archived">Archived</SelectItem>
                        </SelectContent>
                      </Select>
                    )}
                  />
                </div>
                <Button type="submit" disabled={!isDirty || saveMutation.isPending}>
                  {saveMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                  Save Settings
                </Button>
              </form>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
