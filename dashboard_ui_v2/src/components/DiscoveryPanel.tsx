import React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Lightbulb, AlertCircle, Zap, Clock, TrendingUp } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";

/**
 * A small helper component to visualize a priority score as a colored bar.
 * The color changes based on the score's magnitude.
 *
 * @param {object} props - The component props.
 * @param {number} props.score - The priority score to visualize.
 */
const ScoreVisualizer = ({ score }: { score: number }) => {
  // Normalize score to a percentage for the progress bar.
  // The max score is an arbitrary value chosen for good visual representation.
  const maxScoreForVisualization = 200;
  const percentage = Math.min(100, (score / maxScoreForVisualization) * 100);

  let colorClass = "bg-green-500"; // High priority
  if (percentage < 60) colorClass = "bg-yellow-500"; // Medium priority
  if (percentage < 30) colorClass = "bg-orange-500"; // Lower priority

  return (
    <div className="w-full bg-muted rounded-full h-2">
      <div
        className={`${colorClass} h-2 rounded-full transition-all duration-500`}
        style={{ width: `${percentage}%` }}
      ></div>
    </div>
  );
};

/**
 * DiscoveryPanel
 * ==============
 * A React component that fetches and displays personalized automation suggestions
 * for the user. It uses the AI Engine's discovery analytics to find repetitive
 * and time-consuming tasks, presenting them in a ranked list.
 *
 * Features:
 * - Fetches data using TanStack Query.
 * - Displays loading skeletons and handles error states.
 * - Shows a ranked list of suggestions with key metrics.
 * - Visualizes a "priority score" for each suggestion.
 * - Provides an action button to auto-generate a draft workflow.
 */
export function DiscoveryPanel() {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Fetch automation suggestions from the backend API.
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["automationSuggestions"],
    // This assumes `getAutomationSuggestions` is added to the apiClient.
    // If not, it would be: () => fetch("/api/discovery/suggestions").then(r => r.json())
    queryFn: () => apiClient.getAutomationSuggestions(),
  });

  // Mutation to handle the "Generate Workflow" action.
  const generateWorkflowMutation = useMutation({
    mutationFn: (suggestion: any) => {
      // In a real implementation, this would call an API endpoint.
      // e.g., apiClient.generateWorkflowFromSuggestion(suggestion.id)
      console.log("Generating workflow for:", suggestion.title);
      // Simulate API call for demonstration purposes
      return new Promise((resolve) => setTimeout(resolve, 1000));
    },
    onSuccess: () => {
      toast({
        title: "Workflow Generation Started",
        description: "A new draft workflow has been created. You can find it on the Workflows page.",
      });
      // Invalidate workflows query to refetch the list, which will include the new draft.
      queryClient.invalidateQueries({ queryKey: ["workflows"] });
    },
    onError: (err: Error) => {
      toast({
        title: "Generation Failed",
        description: err.message,
        variant: "destructive",
      });
    },
  });

  const handleGenerateClick = (suggestion: any) => {
    generateWorkflowMutation.mutate(suggestion);
  };

  // --- Render Logic ---

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Lightbulb className="h-6 w-6 text-yellow-500 animate-pulse" />
            <span>Scanning for Automation Opportunities...</span>
          </CardTitle>
          <CardDescription>
            Our AI is analyzing your recent activity to find repetitive tasks.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (isError) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Error Loading Suggestions</AlertTitle>
        <AlertDescription>
          Could not load automation suggestions at this time. Please try again later.
          <br />
          <small>{(error as Error).message}</small>
        </AlertDescription>
      </Alert>
    );
  }

  if (!data || !data.suggestions || data.suggestions.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Lightbulb className="h-6 w-6 text-yellow-500" />
            <span>Automation Suggestions</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="text-center py-12">
          <p className="text-muted-foreground">No suggestions found yet.</p>
          <p className="text-sm text-muted-foreground mt-2">
            As you use applications, our AI will learn your patterns and suggest automations here!
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Lightbulb className="h-6 w-6 text-yellow-500" />
          <span>Your Top Automation Opportunities</span>
        </CardTitle>
        <CardDescription>
          Our AI has identified these repetitive tasks as great candidates for automation.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="space-y-4">
          {data.suggestions.map((suggestion: any, index: number) => (
            <li
              key={index}
              className="p-4 border rounded-lg flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 transition-all hover:shadow-md"
            >
              <div className="flex-grow w-full">
                <p className="font-semibold">{suggestion.title}</p>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground mt-2">
                  <span className="flex items-center gap-1">
                    <TrendingUp className="h-4 w-4" /> {suggestion.frequency} times this week
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="h-4 w-4" /> Est. {suggestion.estimated_time_saved_str}
                  </span>
                </div>
                <div className="mt-3">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-xs font-medium text-muted-foreground">
                      Priority Score
                    </span>
                    <span className="text-xs font-bold">{suggestion.priority_score}</span>
                  </div>
                  <ScoreVisualizer score={suggestion.priority_score} />
                </div>
              </div>
              <Button
                size="sm"
                onClick={() => handleGenerateClick(suggestion)}
                disabled={generateWorkflowMutation.isPending}
                className="flex-shrink-0 w-full sm:w-auto mt-3 sm:mt-0"
              >
                <Zap className="mr-2 h-4 w-4" />
                Generate Workflow
              </Button>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
