/**
 * Recording Studio Component
 * ===========================
 * 
 * Advanced recording interface for capturing workflows
 */

import { useState, useEffect, useRef } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Circle, 
  Square, 
  Pause, 
  Play, 
  Save, 
  Trash2,
  Clock,
  Settings,
  Monitor,
  Zap
} from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { toast } from '@/components/ui/use-toast';

import { apiClient, RecordingSession } from '@/lib/api';

interface RecordingEvent {
  id: string;
  type: 'click' | 'type' | 'scroll' | 'navigate' | 'wait';
  timestamp: number;
  description: string;
  element?: string;
  value?: string;
}

const RecordingIndicator: React.FC<{ isRecording: boolean }> = ({ isRecording }) => (
  <motion.div
    className={`flex items-center gap-2 ${isRecording ? 'text-red-500' : 'text-gray-400'}`}
    animate={{ opacity: isRecording ? [1, 0.5, 1] : 1 }}
    transition={{ duration: 1, repeat: isRecording ? Infinity : 0 }}
  >
    <Circle className={`h-3 w-3 ${isRecording ? 'fill-current' : ''}`} />
    <span className="text-sm font-medium">
      {isRecording ? 'Recording...' : 'Ready'}
    </span>
  </motion.div>
);

const Timer: React.FC<{ startTime: number | null; isActive: boolean }> = ({ 
  startTime, 
  isActive 
}) => {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;
    
    if (isActive && startTime) {
      interval = setInterval(() => {
        setElapsed(Date.now() - startTime);
      }, 1000);
    } else if (!isActive) {
      setElapsed(0);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isActive, startTime]);

  const formatTime = (ms: number) => {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  return (
    <div className="flex items-center gap-2 text-sm text-muted-foreground">
      <Clock className="h-4 w-4" />
      <span className="font-mono">{formatTime(elapsed)}</span>
    </div>
  );
};

const EventsList: React.FC<{ events: RecordingEvent[] }> = ({ events }) => (
  <div className="space-y-2 max-h-96 overflow-y-auto">
    <AnimatePresence>
      {events.map((event, index) => (
        <motion.div
          key={event.id}
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 20 }}
          transition={{ duration: 0.2 }}
          className="flex items-center gap-3 p-3 bg-muted/50 rounded-lg"
        >
          <div className="flex-shrink-0">
            <Badge variant="outline" className="text-xs">
              {event.type}
            </Badge>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{event.description}</p>
            {event.element && (
              <p className="text-xs text-muted-foreground truncate">
                Element: {event.element}
              </p>
            )}
            {event.value && (
              <p className="text-xs text-muted-foreground truncate">
                Value: {event.value}
              </p>
            )}
          </div>
          <div className="flex-shrink-0 text-xs text-muted-foreground">
            {new Date(event.timestamp).toLocaleTimeString()}
          </div>
        </motion.div>
      ))}
    </AnimatePresence>
    {events.length === 0 && (
      <div className="text-center py-8 text-muted-foreground">
        <Monitor className="h-12 w-12 mx-auto mb-2 opacity-50" />
        <p>No events recorded yet</p>
        <p className="text-sm">Start recording to capture your actions</p>
      </div>
    )}
  </div>
);

export const RecordingStudio: React.FC = () => {
  const [workflowName, setWorkflowName] = useState('');
  const [currentSession, setCurrentSession] = useState<RecordingSession | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [startTime, setStartTime] = useState<number | null>(null);
  const [recordingEvents, setRecordingEvents] = useState<RecordingEvent[]>([]);
  const [recordingProgress, setRecordingProgress] = useState(0);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const startRecordingMutation = useMutation({
    mutationFn: apiClient.startRecording,
    onSuccess: (session) => {
      setCurrentSession(session);
      setIsRecording(true);
      setStartTime(Date.now());
      setRecordingEvents([]);
      setRecordingProgress(0);
      
      // Simulate recording progress
      intervalRef.current = setInterval(() => {
        setRecordingProgress(prev => Math.min(prev + 1, 100));
      }, 1000);
      
      toast({
        title: "Recording Started",
        description: `Recording workflow: ${session.workflow_name}`,
      });
    },
    onError: (error) => {
      toast({
        title: "Recording Failed",
        description: "Failed to start recording session",
        variant: "destructive",
      });
    },
  });

  const stopRecordingMutation = useMutation({
    mutationFn: (sessionId: string) => apiClient.stopRecording(sessionId),
    onSuccess: () => {
      setIsRecording(false);
      setIsPaused(false);
      setStartTime(null);
      setRecordingProgress(0);
      
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      
      toast({
        title: "Recording Stopped",
        description: "Workflow recording has been saved",
      });
    },
    onError: (error) => {
      toast({
        title: "Stop Failed",
        description: "Failed to stop recording session",
        variant: "destructive",
      });
    },
  });

  const handleStartRecording = () => {
    if (!workflowName.trim()) {
      toast({
        title: "Workflow Name Required",
        description: "Please enter a name for your workflow",
        variant: "destructive",
      });
      return;
    }
    
    startRecordingMutation.mutate(workflowName);
  };

  const handleStopRecording = () => {
    if (currentSession) {
      stopRecordingMutation.mutate(currentSession.session_id);
    }
  };

  const handlePauseResume = () => {
    setIsPaused(!isPaused);
    
    if (isPaused) {
      toast({
        title: "Recording Resumed",
        description: "Continuing to capture events",
      });
    } else {
      toast({
        title: "Recording Paused",
        description: "Event capture paused",
      });
    }
  };

  const simulateRecordingEvent = () => {
    const eventTypes = ['click', 'type', 'scroll', 'navigate', 'wait'] as const;
    const randomType = eventTypes[Math.floor(Math.random() * eventTypes.length)];
    
    const newEvent: RecordingEvent = {
      id: Date.now().toString(),
      type: randomType,
      timestamp: Date.now(),
      description: `Simulated ${randomType} event`,
      element: randomType === 'click' ? 'button.submit' : undefined,
      value: randomType === 'type' ? 'Sample input text' : undefined,
    };
    
    setRecordingEvents(prev => [...prev, newEvent]);
  };

  // Simulate recording events when recording is active
  useEffect(() => {
    if (isRecording && !isPaused) {
      const eventInterval = setInterval(simulateRecordingEvent, 3000);
      return () => clearInterval(eventInterval);
    }
  }, [isRecording, isPaused]);

  const clearEvents = () => {
    setRecordingEvents([]);
    toast({
      title: "Events Cleared",
      description: "All recorded events have been cleared",
    });
  };

  const saveWorkflow = () => {
    toast({
      title: "Workflow Saved",
      description: `Workflow "${workflowName}" saved with ${recordingEvents.length} events`,
    });
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5" />
                Recording Studio
              </CardTitle>
              <CardDescription>
                Capture and record your workflow processes in real-time
              </CardDescription>
            </div>
            <RecordingIndicator isRecording={isRecording} />
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid gap-6 md:grid-cols-2">
            {/* Recording Controls */}
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="workflow-name">Workflow Name</Label>
                <Input
                  id="workflow-name"
                  placeholder="Enter workflow name..."
                  value={workflowName}
                  onChange={(e) => setWorkflowName(e.target.value)}
                  disabled={isRecording}
                />
              </div>
              
              <div className="flex items-center gap-2">
                {!isRecording ? (
                  <Button 
                    onClick={handleStartRecording}
                    disabled={startRecordingMutation.isPending}
                    className="flex-1"
                  >
                    <Circle className="h-4 w-4 mr-2" />
                    Start Recording
                  </Button>
                ) : (
                  <>
                    <Button 
                      onClick={handlePauseResume}
                      variant="outline"
                      size="sm"
                    >
                      {isPaused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
                    </Button>
                    <Button 
                      onClick={handleStopRecording}
                      disabled={stopRecordingMutation.isPending}
                      variant="destructive"
                      className="flex-1"
                    >
                      <Square className="h-4 w-4 mr-2" />
                      Stop Recording
                    </Button>
                  </>
                )}
              </div>
              
              {isRecording && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Timer startTime={startTime} isActive={isRecording && !isPaused} />
                    <span className="text-sm text-muted-foreground">
                      {recordingEvents.length} events
                    </span>
                  </div>
                  <Progress value={recordingProgress} className="h-2" />
                </div>
              )}
              
              {currentSession && (
                <Alert>
                  <AlertDescription>
                    <div className="flex items-center justify-between">
                      <span>Session: {currentSession.session_id}</span>
                      <Badge variant="outline">{currentSession.status}</Badge>
                    </div>
                  </AlertDescription>
                </Alert>
              )}
            </div>

            {/* Recording Settings */}
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Settings className="h-4 w-4" />
                <Label>Recording Settings</Label>
              </div>
              
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm">Capture Screenshots</span>
                  <Badge variant="secondary">Enabled</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm">Record Mouse Movement</span>
                  <Badge variant="secondary">Enabled</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm">Capture Keyboard Input</span>
                  <Badge variant="secondary">Enabled</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm">Auto-pause on Idle</span>
                  <Badge variant="outline">Disabled</Badge>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Recorded Events</CardTitle>
            <div className="flex items-center gap-2">
              <Button 
                variant="outline" 
                size="sm"
                onClick={clearEvents}
                disabled={recordingEvents.length === 0}
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Clear
              </Button>
              <Button 
                variant="outline" 
                size="sm"
                onClick={saveWorkflow}
                disabled={recordingEvents.length === 0}
              >
                <Save className="h-4 w-4 mr-2" />
                Save
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="events" className="w-full">
            <TabsList>
              <TabsTrigger value="events">Events Timeline</TabsTrigger>
              <TabsTrigger value="preview">Workflow Preview</TabsTrigger>
            </TabsList>
            
            <TabsContent value="events" className="mt-4">
              <EventsList events={recordingEvents} />
            </TabsContent>
            
            <TabsContent value="preview" className="mt-4">
              <div className="text-center py-8 text-muted-foreground">
                <p>Workflow preview will be available after recording</p>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
};

export default RecordingStudio;