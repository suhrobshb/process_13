import React, { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useLocation } from "wouter";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
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
import {
  ArrowUpDown,
  MoreHorizontal,
  PlusCircle,
  Trash2,
  Edit,
  Play,
} from "lucide-react";
import { apiClient, Workflow } from "@/lib/api-client";
import { useToast } from "@/components/ui/use-toast";
import { formatDate, capitalize } from "@/lib/utils";

// --- API Functions for TanStack Query ---

const fetchWorkflows = async (): Promise<Workflow[]> => {
  // In a real app, this would be: return apiClient.getWorkflows();
  // For now, we use mock data.
  await new Promise(resolve => setTimeout(resolve, 1000));
  const mockData: Partial<Workflow>[] = [
    { id: 1, name: 'Automated Invoice Processing', status: 'active', created_by: 'admin', updatedAt: new Date().toISOString() },
    { id: 2, name: 'AI-Assisted Contract Review', status: 'draft', created_by: 'legal_team', updatedAt: new Date(Date.now() - 86400000).toISOString() },
    { id: 3, name: 'New Employee Onboarding', status: 'active', created_by: 'hr_admin', updatedAt: new Date(Date.now() - 172800000).toISOString() },
    { id: 4, name: 'Daily Social Media Posting', status: 'archived', created_by: 'marketing', updatedAt: new Date(Date.now() - 259200000).toISOString() },
  ];
  return mockData.map(w => ({ ...w, nodes: [], edges: [], created_at: new Date().toISOString(), description: "A sample workflow." } as Workflow));
};

const deleteWorkflow = async (id: number): Promise<void> => {
  // In a real app: await apiClient.deleteWorkflow(id);
  await new Promise(resolve => setTimeout(resolve, 500));
  console.log(`Workflow ${id} deleted.`);
};

const triggerWorkflow = async (id: number): Promise<{ execution_id: number }> => {
    // In a real app: return apiClient.triggerWorkflow(id);
    await new Promise(resolve => setTimeout(resolve, 500));
    const executionId = Math.floor(Math.random() * 1000);
    console.log(`Workflow ${id} triggered with execution ID ${executionId}.`);
    return { execution_id: executionId };
};

// --- Main Workflows Page Component ---

export default function WorkflowsPage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [, setLocation] = useLocation();

  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [sortBy, setSortBy] = useState<{ field: keyof Workflow; direction: "asc" | "desc" }>({
    field: "updatedAt",
    direction: "desc",
  });

  // Fetching workflows using TanStack Query
  const { data: workflows, isLoading, isError, error } = useQuery<Workflow[], Error>({
    queryKey: ["workflows"],
    queryFn: fetchWorkflows,
  });

  // Mutation for deleting a workflow
  const deleteMutation = useMutation({
    mutationFn: deleteWorkflow,
    onSuccess: () => {
      toast({
        title: "Workflow Deleted",
        description: "The workflow has been successfully deleted.",
      });
      queryClient.invalidateQueries({ queryKey: ["workflows"] });
    },
    onError: (err) => {
      toast({
        title: "Error Deleting Workflow",
        description: err.message,
        variant: "destructive",
      });
    },
  });
  
  // Mutation for triggering a workflow
  const triggerMutation = useMutation({
    mutationFn: triggerWorkflow,
    onSuccess: (data) => {
        toast({
            title: "Workflow Execution Started",
            description: `Execution with ID ${data.execution_id} has begun.`,
        });
        // Optionally navigate to the executions page
        setLocation(`/executions?workflow_id=${data.execution_id}`);
    },
    onError: (err) => {
      toast({
        title: "Error Triggering Workflow",
        description: err.message,
        variant: "destructive",
      });
    },
  });

  // Memoized filtering and sorting logic
  const filteredAndSortedWorkflows = useMemo(() => {
    if (!workflows) return [];
    return workflows
      .filter((wf) => {
        const matchesSearch =
          wf.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          (wf.description && wf.description.toLowerCase().includes(searchTerm.toLowerCase()));
        const matchesStatus = statusFilter === "all" || wf.status === statusFilter;
        return matchesSearch && matchesStatus;
      })
      .sort((a, b) => {
        const fieldA = a[sortBy.field];
        const fieldB = b[sortBy.field];
        let comparison = 0;
        if (fieldA > fieldB) {
          comparison = 1;
        } else if (fieldA < fieldB) {
          comparison = -1;
        }
        return sortBy.direction === "desc" ? -comparison : comparison;
      });
  }, [workflows, searchTerm, statusFilter, sortBy]);

  const handleSort = (field: keyof Workflow) => {
    const isAsc = sortBy.field === field && sortBy.direction === "asc";
    setSortBy({ field, direction: isAsc ? "desc" : "asc" });
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Workflows</h1>
        <Button onClick={() => setLocation("/workflows/new")}>
          <PlusCircle className="mr-2 h-4 w-4" />
          Create Workflow
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Manage Your Workflows</CardTitle>
          <div className="mt-4 flex items-center space-x-4">
            <Input
              placeholder="Search workflows..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="max-w-sm"
            />
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="draft">Draft</SelectItem>
                <SelectItem value="archived">Archived</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead onClick={() => handleSort("name")} className="cursor-pointer">
                  Name <ArrowUpDown className="ml-2 h-4 w-4 inline" />
                </TableHead>
                <TableHead onClick={() => handleSort("status")} className="cursor-pointer">
                  Status <ArrowUpDown className="ml-2 h-4 w-4 inline" />
                </TableHead>
                <TableHead>Created By</TableHead>
                <TableHead onClick={() => handleSort("updatedAt")} className="cursor-pointer text-right">
                  Last Updated <ArrowUpDown className="ml-2 h-4 w-4 inline" />
                </TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={5} className="h-24 text-center">
                    Loading workflows...
                  </TableCell>
                </TableRow>
              ) : isError ? (
                <TableRow>
                  <TableCell colSpan={5} className="h-24 text-center text-red-500">
                    Error: {error.message}
                  </TableCell>
                </TableRow>
              ) : filteredAndSortedWorkflows.length > 0 ? (
                filteredAndSortedWorkflows.map((workflow) => (
                  <TableRow key={workflow.id}>
                    <TableCell className="font-medium">{workflow.name}</TableCell>
                    <TableCell>
                      <Badge variant={workflow.status === 'active' ? 'default' : 'secondary'}>
                        {capitalize(workflow.status)}
                      </Badge>
                    </TableCell>
                    <TableCell>{workflow.created_by || 'N/A'}</TableCell>
                    <TableCell className="text-right">{formatDate(workflow.updatedAt, "PPp")}</TableCell>
                    <TableCell className="text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" className="h-8 w-8 p-0">
                            <span className="sr-only">Open menu</span>
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => triggerMutation.mutate(workflow.id)}>
                            <Play className="mr-2 h-4 w-4" />
                            Run
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => setLocation(`/workflows/${workflow.id}`)}>
                            <Edit className="mr-2 h-4 w-4" />
                            Edit
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={() => deleteMutation.mutate(workflow.id)}
                            className="text-red-600"
                          >
                            <Trash2 className="mr-2 h-4 w-4" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={5} className="h-24 text-center">
                    No workflows found.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
