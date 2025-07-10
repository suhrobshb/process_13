import { Button } from "@/components/ui/button";
import { ArrowUpRight, TrendingUp, Zap } from "lucide-react";
import { DashboardStatsCards } from "@/components/dashboard/DashboardStatsCards";
import { RecentWorkflowsTable } from "@/components/dashboard/RecentWorkflowsTable";
import { ROIChart } from "@/components/analytics/ROIChart";
import { RecordingStudio } from "@/components/recording/RecordingStudio";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

// --- Main Dashboard Page Component ---

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between space-y-2">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Monitor your automation workflows and system performance
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button variant="outline">
            <TrendingUp className="mr-2 h-4 w-4" />
            Analytics
          </Button>
          <Button>
            <ArrowUpRight className="mr-2 h-4 w-4" />
            Export Report
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <DashboardStatsCards />

      {/* Main Dashboard Content */}
      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
          <TabsTrigger value="recording">Recording</TabsTrigger>
          <TabsTrigger value="workflows">Workflows</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <RecentWorkflowsTable />
            </div>
            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Zap className="h-5 w-5" />
                    Quick Actions
                  </CardTitle>
                  <CardDescription>
                    Commonly used workflow actions
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <Button className="w-full" variant="outline">
                    Create New Workflow
                  </Button>
                  <Button className="w-full" variant="outline">
                    Import Workflow
                  </Button>
                  <Button className="w-full" variant="outline">
                    Run Scheduled Tasks
                  </Button>
                  <Button className="w-full" variant="outline">
                    View System Logs
                  </Button>
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="analytics" className="space-y-6">
          <ROIChart />
        </TabsContent>

        <TabsContent value="recording" className="space-y-6">
          <RecordingStudio />
        </TabsContent>

        <TabsContent value="workflows" className="space-y-6">
          <RecentWorkflowsTable />
        </TabsContent>
      </Tabs>
    </div>
  );
}
