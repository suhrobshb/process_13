import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import {
  Activity,
  ArrowUpRight,
  Clock,
  Cpu,
  Database,
  GitFork,
  HeartPulse,
  Save,
} from "lucide-react";
import { formatDate, capitalize } from "@/lib/utils";
import { apiClient, Workflow, Execution } from "@/lib/api-client";

// --- Mock API Fetching Functions ---
// In a real app, these would be part of the apiClient, but for this component
// we define them here to show how TanStack Query is used.

const getDashboardStats = async () => {
  // Mock data, replace with API call: await apiClient.getDashboardStats()
  await new Promise(resolve => setTimeout(resolve, 500));
  return {
    workflowsAutomated: 42,
    hoursSavedMonthly: 128,
    processAccuracy: 0.997,
    executionsToday: 73,
  };
};

const getRecentWorkflows = async (): Promise<Workflow[]> => {
  // Mock data, replace with API call: await apiClient.getWorkflows({ limit: 5 })
  await new Promise(resolve => setTimeout(resolve, 800));
  const mockData: Partial<Workflow>[] = [
    { id: 1, name: 'Automated Invoice Processing', status: 'active', updatedAt: new Date().toISOString() },
    { id: 2, name: 'AI-Assisted Contract Review', status: 'active', updatedAt: new Date(Date.now() - 3600000).toISOString() },
    { id: 3, name: 'New Employee Onboarding', status: 'draft', updatedAt: new Date(Date.now() - 86400000).toISOString() },
    { id: 4, name: 'Daily Social Media Posting', status: 'archived', updatedAt: new Date(Date.now() - 172800000).toISOString() },
  ];
  // We need to cast to full Workflow type for consistency
  return mockData.map(w => ({ ...w, nodes: [], edges: [], created_at: new Date().toISOString() } as Workflow));
};

const getRecentExecutions = async (): Promise<Execution[]> => {
  // Mock data, replace with API call: await apiClient.getExecutions({ limit: 5 })
  await new Promise(resolve => setTimeout(resolve, 1200));
  const mockData: Partial<Execution>[] = [
    { id: 101, workflow_id: 1, status: 'completed', completed_at: new Date().toISOString() },
    { id: 102, workflow_id: 2, status: 'failed', completed_at: new Date(Date.now() - 120000).toISOString(), error: 'API connection timeout' },
    { id: 103, workflow_id: 1, status: 'running', started_at: new Date(Date.now() - 60000).toISOString() },
    { id: 104, workflow_id: 3, status: 'completed', completed_at: new Date(Date.now() - 300000).toISOString() },
  ];
  return mockData.map(e => ({ ...e, started_at: new Date().toISOString() } as Execution));
};

const getSystemHealth = async () => {
    // Mock data, replace with API call: await apiClient.getSystemHealth()
    await new Promise(resolve => setTimeout(resolve, 300));
    return {
        apiStatus: 'operational',
        databaseStatus: 'operational',
        aiLearningEngineStatus: 'operational',
        celeryWorkers: 4,
    };
};


// --- Dashboard Components ---

const StatsCard = ({ title, value, description, icon: Icon }) => (
  <Card>
    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
      <CardTitle className="text-sm font-medium">{title}</CardTitle>
      <Icon className="h-4 w-4 text-muted-foreground" />
    </CardHeader>
    <CardContent>
      <div className="text-2xl font-bold">{value}</div>
      <p className="text-xs text-muted-foreground">{description}</p>
    </CardContent>
  </Card>
);

const RecentWorkflows = () => {
  const { data: workflows, isLoading, isError } = useQuery({ 
    queryKey: ['recentWorkflows'], 
    queryFn: getRecentWorkflows 
  });

  if (isLoading) return <Card><CardHeader><CardTitle>Recent Workflows</CardTitle></CardHeader><CardContent>Loading...</CardContent></Card>;
  if (isError) return <Card><CardHeader><CardTitle>Recent Workflows</CardTitle></CardHeader><CardContent>Error loading workflows.</CardContent></Card>;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Workflows</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Last Updated</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {workflows?.map((workflow) => (
              <TableRow key={workflow.id}>
                <TableCell className="font-medium">{workflow.name}</TableCell>
                <TableCell>
                  <Badge variant={workflow.status === 'active' ? 'default' : 'secondary'}>
                    {capitalize(workflow.status)}
                  </Badge>
                </TableCell>
                <TableCell className="text-right">{formatDate(workflow.updatedAt, "PPp")}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
};

const RecentExecutions = () => {
    const { data: executions, isLoading, isError } = useQuery({ 
        queryKey: ['recentExecutions'], 
        queryFn: getRecentExecutions 
    });

    if (isLoading) return <Card><CardHeader><CardTitle>Recent Executions</CardTitle></CardHeader><CardContent>Loading...</CardContent></Card>;
    if (isError) return <Card><CardHeader><CardTitle>Recent Executions</CardTitle></CardHeader><CardContent>Error loading executions.</CardContent></Card>;

    return (
        <Card>
            <CardHeader>
                <CardTitle>Recent Executions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                {executions?.map(exec => (
                    <div key={exec.id} className="flex items-center">
                        <div className="flex-shrink-0">
                            {exec.status === 'completed' && <div className="h-8 w-8 rounded-full bg-green-500 flex items-center justify-center"><Check className="h-4 w-4 text-white" /></div>}
                            {exec.status === 'failed' && <div className="h-8 w-8 rounded-full bg-red-500 flex items-center justify-center"><X className="h-4 w-4 text-white" /></div>}
                            {exec.status === 'running' && <div className="h-8 w-8 rounded-full bg-blue-500 flex items-center justify-center animate-pulse"><Activity className="h-4 w-4 text-white" /></div>}
                        </div>
                        <div className="ml-4">
                            <p className="text-sm font-medium">Workflow #{exec.workflow_id}</p>
                            <p className="text-sm text-muted-foreground">
                                {capitalize(exec.status)} - {formatDate(exec.completed_at || exec.started_at, 'Pp')}
                            </p>
                        </div>
                    </div>
                ))}
            </CardContent>
        </Card>
    );
};

const SystemHealth = () => {
    const { data: health, isLoading, isError } = useQuery({ 
        queryKey: ['systemHealth'], 
        queryFn: getSystemHealth 
    });

    if (isLoading) return <Card><CardHeader><CardTitle>System Health</CardTitle></CardHeader><CardContent>Loading...</CardContent></Card>;
    if (isError) return <Card><CardHeader><CardTitle>System Health</CardTitle></CardHeader><CardContent>Error loading health status.</CardContent></Card>;

    const StatusItem = ({ label, status }) => (
        <div className="flex justify-between items-center text-sm">
            <span className="text-muted-foreground">{label}</span>
            <span className={`font-semibold ${status === 'operational' ? 'text-green-600' : 'text-red-600'}`}>
                {capitalize(status)}
            </span>
        </div>
    );

    return (
        <Card>
            <CardHeader>
                <CardTitle>System Health</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
                <StatusItem label="API Status" status={health.apiStatus} />
                <StatusItem label="Database" status={health.databaseStatus} />
                <StatusItem label="AI Learning Engine" status={health.aiLearningEngineStatus} />
                <div className="flex justify-between items-center text-sm">
                    <span className="text-muted-foreground">Celery Workers</span>
                    <span className="font-semibold">{health.celeryWorkers} Active</span>
                </div>
            </CardContent>
        </Card>
    );
};


// --- Main Dashboard Page Component ---

export default function DashboardPage() {
  const { data: stats, isLoading: isLoadingStats } = useQuery({ 
    queryKey: ['dashboardStats'], 
    queryFn: getDashboardStats 
  });

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <div className="flex items-center space-x-2">
          <Button>
            <ArrowUpRight className="mr-2 h-4 w-4" />
            Export Report
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {isLoadingStats ? (
            Array.from({ length: 4 }).map((_, i) => <Card key={i} className="h-[120px] animate-pulse bg-gray-200" />)
        ) : (
            <>
                <StatsCard title="Workflows Automated" value={stats.workflowsAutomated} description="+5 this week" icon={GitFork} />
                <StatsCard title="Hours Saved (Monthly)" value={stats.hoursSavedMonthly} description="Equivalent to 0.8 FTE" icon={Clock} />
                <StatsCard title="Process Accuracy" value={`${(stats.processAccuracy * 100).toFixed(1)}%`} description="Up from 92% manual" icon={HeartPulse} />
                <StatsCard title="Executions Today" value={stats.executionsToday} description="Peak at 2 PM" icon={Activity} />
            </>
        )}
      </div>

      {/* Recent Activity Section */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        <div className="lg:col-span-4">
            <RecentWorkflows />
        </div>
        <div className="lg:col-span-3 grid gap-4">
            <RecentExecutions />
            <SystemHealth />
        </div>
      </div>
    </div>
  );
}
