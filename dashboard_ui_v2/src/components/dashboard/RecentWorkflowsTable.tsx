/**
 * Recent Workflows Table Component
 * =================================
 * 
 * Modern table showing recent workflow activity with actions
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { 
  Play, 
  Edit, 
  MoreHorizontal, 
  RefreshCw,
  Eye,
  Copy,
  Trash2
} from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { toast } from '@/components/ui/use-toast';

import { apiClient, queryKeys, RecentWorkflow } from '@/lib/api';

const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const variants = {
    active: 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400',
    draft: 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400',
    error: 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400',
    paused: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400',
  };

  return (
    <Badge 
      variant="secondary" 
      className={variants[status as keyof typeof variants] || variants.draft}
    >
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </Badge>
  );
};

const EfficiencyBadge: React.FC<{ efficiency: number }> = ({ efficiency }) => {
  const getColor = () => {
    if (efficiency >= 95) return 'text-green-600';
    if (efficiency >= 85) return 'text-blue-600';
    if (efficiency >= 75) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <span className={`font-medium ${getColor()}`}>
      {efficiency.toFixed(1)}%
    </span>
  );
};

const WorkflowRow: React.FC<{ workflow: RecentWorkflow; index: number }> = ({ 
  workflow, 
  index 
}) => {
  const [isActionLoading, setIsActionLoading] = useState(false);

  const handleAction = async (action: string) => {
    setIsActionLoading(true);
    try {
      switch (action) {
        case 'run':
          toast({
            title: "Workflow Started",
            description: `Running workflow: ${workflow.name}`,
          });
          break;
        case 'edit':
          toast({
            title: "Opening Editor",
            description: `Editing workflow: ${workflow.name}`,
          });
          break;
        case 'duplicate':
          toast({
            title: "Workflow Duplicated",
            description: `Created copy of: ${workflow.name}`,
          });
          break;
        case 'delete':
          toast({
            title: "Workflow Deleted",
            description: `Deleted workflow: ${workflow.name}`,
            variant: "destructive",
          });
          break;
      }
    } catch (error) {
      toast({
        title: "Action Failed",
        description: "Please try again",
        variant: "destructive",
      });
    } finally {
      setIsActionLoading(false);
    }
  };

  return (
    <motion.tr
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.1 }}
      className="hover:bg-muted/50 transition-colors"
    >
      <TableCell className="font-medium">{workflow.name}</TableCell>
      <TableCell>
        <StatusBadge status={workflow.status} />
      </TableCell>
      <TableCell className="text-muted-foreground">{workflow.last_run}</TableCell>
      <TableCell>
        <EfficiencyBadge efficiency={workflow.efficiency} />
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleAction('run')}
            disabled={isActionLoading}
          >
            <Play className="h-3 w-3 mr-1" />
            Run
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleAction('edit')}
            disabled={isActionLoading}
          >
            <Edit className="h-3 w-3 mr-1" />
            Edit
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Actions</DropdownMenuLabel>
              <DropdownMenuItem onClick={() => handleAction('view')}>
                <Eye className="h-4 w-4 mr-2" />
                View Details
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleAction('duplicate')}>
                <Copy className="h-4 w-4 mr-2" />
                Duplicate
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem 
                onClick={() => handleAction('delete')}
                className="text-red-600"
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </TableCell>
    </motion.tr>
  );
};

const TableSkeleton: React.FC = () => (
  <TableBody>
    {[1, 2, 3, 4, 5].map((i) => (
      <TableRow key={i}>
        <TableCell><Skeleton className="h-4 w-48" /></TableCell>
        <TableCell><Skeleton className="h-5 w-16" /></TableCell>
        <TableCell><Skeleton className="h-4 w-32" /></TableCell>
        <TableCell><Skeleton className="h-4 w-12" /></TableCell>
        <TableCell>
          <div className="flex gap-2">
            <Skeleton className="h-8 w-16" />
            <Skeleton className="h-8 w-16" />
            <Skeleton className="h-8 w-8" />
          </div>
        </TableCell>
      </TableRow>
    ))}
  </TableBody>
);

export const RecentWorkflowsTable: React.FC = () => {
  const { data: workflows, isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.recentWorkflows,
    queryFn: apiClient.getRecentWorkflows,
    refetchInterval: 60000, // Refresh every minute
  });

  const handleRefresh = () => {
    refetch();
    toast({
      title: "Refreshed",
      description: "Workflows data updated",
    });
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Recent Workflows</CardTitle>
            <CardDescription>
              View and manage your workflow executions
            </CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isLoading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {error ? (
          <div className="text-center py-8">
            <p className="text-muted-foreground">Failed to load workflows</p>
            <Button 
              variant="outline" 
              onClick={handleRefresh}
              className="mt-2"
            >
              Try Again
            </Button>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Last Run</TableHead>
                <TableHead>Efficiency</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            {isLoading ? (
              <TableSkeleton />
            ) : (
              <TableBody>
                {workflows?.map((workflow, index) => (
                  <WorkflowRow 
                    key={workflow.id} 
                    workflow={workflow} 
                    index={index}
                  />
                ))}
                {workflows?.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-8">
                      <p className="text-muted-foreground">No workflows found</p>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            )}
          </Table>
        )}
      </CardContent>
    </Card>
  );
};

export default RecentWorkflowsTable;