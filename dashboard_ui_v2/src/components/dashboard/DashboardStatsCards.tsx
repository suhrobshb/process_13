/**
 * Dashboard Stats Cards Component
 * ================================
 * 
 * Modern dashboard statistics cards with real-time updates
 */

import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { 
  Activity, 
  Clock, 
  Target, 
  Workflow,
  TrendingUp,
  TrendingDown,
  Minus
} from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { apiClient, queryKeys } from '@/lib/api';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle: string;
  icon: React.ReactNode;
  trend?: {
    value: number;
    label: string;
  };
  color: 'blue' | 'green' | 'purple' | 'orange';
}

const StatCard: React.FC<StatCardProps> = ({ 
  title, 
  value, 
  subtitle, 
  icon, 
  trend,
  color 
}) => {
  const colorClasses = {
    blue: 'bg-blue-100 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400',
    green: 'bg-green-100 text-green-600 dark:bg-green-900/20 dark:text-green-400',
    purple: 'bg-purple-100 text-purple-600 dark:bg-purple-900/20 dark:text-purple-400',
    orange: 'bg-orange-100 text-orange-600 dark:bg-orange-900/20 dark:text-orange-400',
  };

  const getTrendIcon = () => {
    if (!trend) return <Minus className="h-3 w-3" />;
    return trend.value > 0 ? (
      <TrendingUp className="h-3 w-3" />
    ) : (
      <TrendingDown className="h-3 w-3" />
    );
  };

  const getTrendColor = () => {
    if (!trend) return 'text-gray-500';
    return trend.value > 0 ? 'text-green-600' : 'text-red-600';
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      whileHover={{ scale: 1.02 }}
    >
      <Card className="relative overflow-hidden">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">{title}</CardTitle>
          <div className={`p-2 rounded-lg ${colorClasses[color]}`}>
            {icon}
          </div>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{value}</div>
          <div className="flex items-center justify-between mt-2">
            <p className="text-xs text-muted-foreground">{subtitle}</p>
            {trend && (
              <Badge variant="secondary" className={`${getTrendColor()} text-xs`}>
                {getTrendIcon()}
                <span className="ml-1">{trend.label}</span>
              </Badge>
            )}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
};

const StatsCardSkeleton: React.FC = () => (
  <Card>
    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
      <Skeleton className="h-4 w-32" />
      <Skeleton className="h-8 w-8 rounded-lg" />
    </CardHeader>
    <CardContent>
      <Skeleton className="h-8 w-16 mb-2" />
      <div className="flex items-center justify-between">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-4 w-12" />
      </div>
    </CardContent>
  </Card>
);

export const DashboardStatsCards: React.FC = () => {
  const { data: stats, isLoading, error } = useQuery({
    queryKey: queryKeys.dashboardStats,
    queryFn: apiClient.getDashboardStats,
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <StatsCardSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i} className="border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20">
            <CardContent className="p-6">
              <div className="text-sm text-red-600 dark:text-red-400">
                Failed to load stats
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (!stats) return null;

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <StatCard
        title="Workflows Automated"
        value={stats.workflows_count}
        subtitle={`${stats.active_workflows} active workflows`}
        icon={<Workflow className="h-4 w-4" />}
        trend={{ value: 12, label: '+12%' }}
        color="blue"
      />
      
      <StatCard
        title="Hours Saved (Monthly)"
        value={stats.hours_saved}
        subtitle={`Equivalent to ${(stats.hours_saved / 160).toFixed(1)} FTE`}
        icon={<Clock className="h-4 w-4" />}
        trend={{ value: 18, label: '+18%' }}
        color="green"
      />
      
      <StatCard
        title="Process Accuracy"
        value={`${stats.process_accuracy}%`}
        subtitle="Up from 92% manual"
        icon={<Target className="h-4 w-4" />}
        trend={{ value: 2.3, label: '+2.3%' }}
        color="purple"
      />
      
      <StatCard
        title="Executions Today"
        value={stats.executions_today}
        subtitle="Peak at 2 PM"
        icon={<Activity className="h-4 w-4" />}
        trend={{ value: 0, label: 'Today' }}
        color="orange"
      />
    </div>
  );
};

export default DashboardStatsCards;