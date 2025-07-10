import React, { useState, useMemo, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
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
  FileText,
  RefreshCw,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
} from "lucide-react";
import { apiClient, Execution, Workflow } from "@/lib/api-client";
import { useToast } from "@/components/ui/use-toast";
import { formatDate, capitalize } from "@/lib/utils";

// --- API Functions for TanStack Query ---

// In a real app, these would be part of the apiClient.
const fetchExecutions = async (): Promise<Execution[]> => {
  // Mock data, replace with: return apiClient.getExecutions();
  await new Promise(resolve => setTimeout(resolve, 1000));
  const mockData: Partial<Execution>[] = [
    { id: 101, workflow_id: 1, status: 'completed', started_at: new Date(Date.now() - 3600000).toISOString(), completed_at: new Date(Date.now() - 3540000).toISOString() },
    { id: 102, workflow_id: 2, status: 'failed', started_at: new Date(Date.now() - 7200000).toISOString(), completed_at: new Date(Date.now() - 7180000).toISOString(), error: 'API connection timeout' },
    { id: 103, workflow_id: 1, status: 'running', started_at: new Date().toISOString() },
    { id: 104, workflow_id: 3, status: 'completed', started_at: new Date(Date.now() - 86400000).toISOString(), completed_at: new Date(Date.now() - 86300000).toISOString() },
  ];
  // Add workflow names for display
  return mockData.map(e => ({ ...e, workflowName: `Workflow #${e.workflow_id}` } as any));
};

const fetchWorkflows = async (): Promise<Workflow[]> => {
    // Mock data, replace with: return apiClient.getWorkflows();
    const mockData: Partial<Workflow>[] = [
      { id: 1, name: 'Automated Invoice Processing' },
      { id: 2, name: 'AI-Assisted Contract Review' },
      { id: 3, name: 'New Employee Onboarding' },
    ];
    return mockData.map(w => ({ ...w, nodes: [], edges: [], created_at: new Date().toISOString(), updatedAt: new Date().toISOString(), description: "", status: "active" } as Workflow));
};

// --- Helper Components ---

const StatusBadge = ({ status }: { status: string }) => {
  const statusStyles = {
    completed: "bg-green-100 text-green-800",
    failed: "bg-red-100 text-red-800",
    running: "bg-blue-100 text-blue-800",
    pending: "bg-yellow-100 text-yellow-800",
  };
  const Icon = {
    completed: CheckCircle2,
    failed: XCircle,
    running: Loader2,
    pending: Clock,
  }[status];

  return (
    <Badge variant="outline" className={`border-transparent ${statusStyles[status]}`}>
      <Icon className={`mr-1 h-3 w-3 ${status === 'running' && 'animate-spin'}`} />
      {capitalize(status)}
    </Badge>
  );
};

// --- Main Executions Page Component ---

export default function ExecutionsPage() {
  const { toast } = useToast();
  const [, setLocation] = useLocation();

  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [sortBy, setSortBy] = useState<{ field: keyof Execution; direction: "asc" | "desc" }>({
    field: "started_at",
    direction: "desc",
  });

  // Fetch executions with real-time polling for running workflows
  const { data: executions, isLoading, isError, error } = useQuery<Execution[], Error>({
    queryKey: ["executions"],
    queryFn: fetchExecutions,
    refetchInterval: (query) => {
      const data = query.state.data as Execution[] | undefined;
      // If there are any running workflows, poll every 5 seconds. Otherwise, disable polling.
      return data?.some(e => e.status === 'running') ? 5000 : false;
    },
  });

  // Fetch workflows to map names to executions
  const { data: workflows } = useQuery<Workflow[], Error>({
    queryKey: ["workflows"],
    queryFn: fetchWorkflows,
  });

  // Memoized data processing
  const processedExecutions = useMemo(() => {
    if (!executions || !workflows) return [];
    
    const workflowMap = new Map(workflows.map(wf => [wf.id, wf.name]));

    return executions
      .map(exec => ({
        ...exec,
        workflowName: workflowMap.get(exec.workflow_id) || `Workflow #${exec.workflow_id}`,
        duration: exec.completed_at && exec.started_at 
          ? ((new Date(exec.completed_at).getTime() - new Date(exec.started_at).getTime()) / 1000).toFixed(2) + 's'
          : 'N/A',
      }))
      .filter((exec) => {
        const matchesSearch = exec.workflowName.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesStatus = statusFilter === "all" || exec.status === statusFilter;
        return matchesSearch && matchesStatus;
      })
      .sort((a, b) => {
        const fieldA = a[sortBy.field];
        const fieldB = b[sortBy.field];
        if (fieldA === null || fieldA === undefined) return 1;
        if (fieldB === null || fieldB === undefined) return -1;
        let comparison = 0;
        if (fieldA > fieldB) {
          comparison = 1;
        } else if (fieldA < fieldB) {
          comparison = -1;
        }
        return sortBy.direction === "desc" ? -comparison : comparison;
      });
  }, [executions, workflows, searchTerm, statusFilter, sortBy]);

  const handleSort = (field: keyof Execution) => {
    const isAsc = sortBy.field === field && sortBy.direction === "asc";
    setSortBy({ field, direction: isAsc ? "desc" : "asc" });
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Workflow Executions</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Execution History</CardTitle>
          <div className="mt-4 flex items-center space-x-4">
            <Input
              placeholder="Search by workflow name..."
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
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
                <SelectItem value="running">Running</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Execution ID</TableHead>
                <TableHead onClick={() => handleSort("workflowName" as any)} className="cursor-pointer">
                  Workflow Name <ArrowUpDown className="ml-2 h-4 w-4 inline" />
                </TableHead>
                <TableHead onClick={() => handleSort("status")} className="cursor-pointer">
                  Status <ArrowUpDown className="ml-2 h-4 w-4 inline" />
                </TableHead>
                <TableHead onClick={() => handleSort("started_at")} className="cursor-pointer">
                  Started At <ArrowUpDown className="ml-2 h-4 w-4 inline" />
                </TableHead>
                <TableHead>Duration</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={6} className="h-24 text-center">
                    Loading executions...
                  </TableCell>
                </TableRow>
              ) : isError ? (
                <TableRow>
                  <TableCell colSpan={6} className="h-24 text-center text-red-500">
                    Error: {error.message}
                  </TableCell>
                </TableRow>
              ) : processedExecutions.length > 0 ? (
                processedExecutions.map((exec) => (
                  <TableRow key={exec.id}>
                    <TableCell className="font-mono text-xs">{exec.id}</TableCell>
                    <TableCell className="font-medium">{exec.workflowName}</TableCell>
                    <TableCell>
                      <StatusBadge status={exec.status} />
                    </TableCell>
                    <TableCell>{formatDate(exec.started_at, "PPp")}</TableCell>
                    <TableCell>{exec.duration}</TableCell>
                    <TableCell className="text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" className="h-8 w-8 p-0">
                            <span className="sr-only">Open menu</span>
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => alert(`Viewing details for execution ${exec.id}`)}>
                            <FileText className="mr-2 h-4 w-4" />
                            View Details & Logs
                          </DropdownMenuItem>
                          {exec.status === 'failed' && (
                            <DropdownMenuItem onClick={() => alert(`Retrying execution ${exec.id}`)}>
                              <RefreshCw className="mr-2 h-4 w-4" />
                              Retry Failed Steps
                            </DropdownMenuItem>
                          )}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={6} className="h-24 text-center">
                    No executions found.
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
