import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Switch, Route, Router } from "wouter";

import { ThemeProvider } from "@/components/layout/theme-provider";
import { Toaster } from "@/components/ui/toaster";
import { MainLayout } from "@/components/layout/main-layout";
import { AuthProvider } from "@/contexts/AuthContext";

// Import Pages
import DashboardPage from "@/pages/DashboardPage";
import RecordingPage from "@/pages/RecordingPage";
import WorkflowsPage from "@/pages/WorkflowsPage";
import WorkflowDetailPage from "@/pages/WorkflowDetailPage";
import AdvancedWorkflowPage from "@/pages/AdvancedWorkflowPage";
import ExecutionsPage from "@/pages/ExecutionsPage";
import SettingsPage from "@/pages/SettingsPage";
import LoginPage from "@/pages/LoginPage";
import RegisterPage from "@/pages/RegisterPage";
import NotFoundPage from "@/pages/NotFoundPage";

// Create a client for TanStack Query
const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ThemeProvider defaultTheme="system" storageKey="ai-engine-ui-theme">
          <Router>
            <Switch>
            {/* Authentication Routes */}
            <Route path="/login">
              <LoginPage />
            </Route>
            <Route path="/register">
              <RegisterPage />
            </Route>
            
            {/* Main User Interface Routes */}
            <Route path="/">
              <MainLayout>
                <DashboardPage />
              </MainLayout>
            </Route>
            <Route path="/recording">
              <MainLayout>
                <RecordingPage />
              </MainLayout>
            </Route>
            <Route path="/workflows">
              <MainLayout>
                <WorkflowsPage />
              </MainLayout>
            </Route>
            <Route path="/workflows/:id">
              {(params) => (
                <MainLayout>
                  <WorkflowDetailPage id={params.id} />
                </MainLayout>
              )}
            </Route>
            <Route path="/workflows/:id/advanced">
              {(params) => (
                <AdvancedWorkflowPage />
              )}
            </Route>
            <Route path="/executions">
              <MainLayout>
                <ExecutionsPage />
              </MainLayout>
            </Route>
            <Route path="/settings">
              <MainLayout>
                <SettingsPage />
              </MainLayout>
            </Route>

            {/* Admin Routes (can be expanded later) */}
            {/* 
            <Route path="/admin/:rest*">
              <AdminLayout>
                <Switch>
                  <Route path="/admin" component={AdminDashboardPage} />
                  <Route path="/admin/users" component={AdminUsersPage} />
                </Switch>
              </AdminLayout>
            </Route> 
            */}

            {/* Fallback 404 Page */}
            <Route>
              <NotFoundPage />
            </Route>
          </Switch>
          </Router>
          <Toaster />
        </ThemeProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
