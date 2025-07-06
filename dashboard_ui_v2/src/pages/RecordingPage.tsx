import React, { useState, useEffect, useRef } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Bot,
  Circle,
  Cpu,
  FileText,
  Loader2,
  MousePointerClick,
  Play,
  Square,
  Type,
  Video,
  Save,
  PenSquare,
} from "lucide-react";
import { v4 as uuidv4 } from "uuid";
import { useLocation } from "wouter";
import VisualWorkflowEditor from "@/components/workflow-editor/VisualWorkflowEditor";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { capitalize } from "@/lib/utils";
import { apiClient } from "@/lib/api-client";
import { useToast } from "@/components/ui/use-toast";
import { useWebSocket } from "@/hooks/useWebSocket";

// --- Mock Data for Local Event Simulation ---
// This simulates the events captured by a local recording agent.
const mockEventStream = [
  { type: "window_change", details: { title: "Inbox - user@company.com - Outlook" } },
  { type: "click", details: { x: 250, y: 300, element: "Email: New PO #12345" } },
  { type: "double_click", details: { x: 400, y: 500, element: "po_12345.pdf" } },
  { type: "wait", details: { duration: 1.5 } },
  { type: "window_change", details: { title: "po_12345.pdf - Adobe Reader" } },
  { type: "hotkey", details: { keys: ["ctrl", "c"] } },
  { type: "window_change", details: { title: "Customer Portal - Google Chrome" } },
  { type: "type", details: { text: "Acme Corp", element: "Search Input" } },
  { type: "press", details: { key: "Enter" } },
  { type: "wait", details: { duration: 2.0 } },
  { type: "click", details: { x: 800, y: 400, element: "New Order Button" } },
  { type: "type", details: { text: "PO12345", element: "PO Number Field" } },
  { type: "hotkey", details: { keys: ["ctrl", "v"] } },
  { type: "click", details: { x: 950, y: 700, element: "Save Order Button" } },
];

// --- Helper Components ---

const StatusIndicator = ({ isRecording, isProcessing }) => {
  let text = "Not Recording";
  let dotColor = "bg-gray-400";
  if (isRecording) {
    text = "Recording & Analyzing...";
    dotColor = "bg-red-500 animate-pulse";
  } else if (isProcessing) {
    text = "Finalizing Workflow...";
    dotColor = "bg-blue-500 animate-spin";
  }

  return (
    <div className="flex items-center space-x-2">
      <div className={`w-3 h-3 rounded-full ${dotColor}`}></div>
      <span className="font-semibold text-lg">{text}</span>
    </div>
  );
};

const EventIcon = ({ type }) => {
    switch (type) {
        case 'click':
        case 'double_click':
            return <MousePointerClick className="h-4 w-4 text-blue-500" />;
        case 'type':
        case 'hotkey':
        case 'press':
            return <Type className="h-4 w-4 text-green-500" />;
        case 'window_change':
            return <Video className="h-4 w-4 text-purple-500" />;
        default:
            return <Circle className="h-4 w-4 text-gray-400" />;
    }
};

const EventFeed = ({ events }) => (
  <ScrollArea className="h-full">
    <div className="space-y-4 p-4">
      {events.map((event, index) => (
        <div key={index} className="flex items-start space-x-3">
          <EventIcon type={event.type} />
          <div className="flex-1">
            <p className="text-sm font-medium">{capitalize(event.type.replace('_', ' '))}</p>
            <p className="text-xs text-muted-foreground">
              {JSON.stringify(event.details)}
            </p>
          </div>
          <span className="text-xs text-muted-foreground">{new Date(event.timestamp).toLocaleTimeString()}</span>
        </div>
      ))}
      {events.length === 0 && <p className="text-sm text-muted-foreground text-center py-16">Start recording to see events appear here...</p>}
    </div>
  </ScrollArea>
);

// --- Main Recording Page Component ---

export default function RecordingPage() {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [capturedEvents, setCapturedEvents] = useState([]);
  const [workflowNodes, setWorkflowNodes] = useState([]);
  const [workflowEdges, setWorkflowEdges] = useState([]);
  const [generatedWorkflow, setGeneratedWorkflow] = useState(null);
  const [clientId, setClientId] = useState(uuidv4());
  
  const timerRef = useRef(null);
  const eventSimulatorRef = useRef(null);
  const [, setLocation] = useLocation();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const createWorkflowMutation = useMutation({
    mutationFn: (workflowData) => apiClient.createWorkflow(workflowData),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["workflows"] });
      toast({ title: "Success", description: "Workflow saved successfully. Redirecting..." });
      setLocation(`/workflows/${data.id}`);
    },
    onError: (error) => {
      toast({ title: "Error", description: `Failed to save workflow: ${error.message}`, variant: "destructive" });
    },
  });

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (eventSimulatorRef.current) clearInterval(eventSimulatorRef.current);
    };
  }, []);

  /* ------------------------------------------------------------------ */
  /* WebSocket – live updates while recording                           */
  /* ------------------------------------------------------------------ */

  const { lastMessage } = useWebSocket(
    // Connect only while recording; disconnect when recording stops.
    isRecording ? apiClient.getWebSocketUrl(clientId) : null,
    {
      onOpen: () =>
        toast({
          title: "Connected",
          description: "Real-time analysis session started.",
        }),
      onError: () =>
        toast({
          title: "Connection Error",
          variant: "destructive",
        }),
    }
  );

  // React to streaming messages
  useEffect(() => {
    if (lastMessage) handleWebSocketMessage(lastMessage as MessageEvent);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lastMessage]);

  const handleWebSocketMessage = (event: MessageEvent) => {
    try {
      const message = JSON.parse(event.data);
      switch (message.type) {
        case 'NEW_WORKFLOW_NODE':
          const newNode = {
            ...message.payload,
            type: 'actionStep', // Ensure it uses our custom node type
            position: { x: 250, y: 100 + workflowNodes.length * 200 },
          };
          setWorkflowNodes(prevNodes => {
            const newNodes = [...prevNodes, newNode];
            if (newNodes.length > 1) {
              const newEdge = {
                id: `e${newNodes[newNodes.length - 2].id}-${newNode.id}`,
                source: newNodes[newNodes.length - 2].id,
                target: newNode.id,
                animated: true,
              };
              setWorkflowEdges(prevEdges => [...prevEdges, newEdge]);
            }
            return newNodes;
          });
          break;
        case 'ANALYSIS_COMPLETE':
          setGeneratedWorkflow(message.payload);
          setIsProcessing(false);
          toast({ title: "Analysis Complete", description: "Your workflow is ready to be saved." });
          ws.current?.close();
          break;
        case 'ANALYSIS_FAILED':
          toast({ title: "Analysis Failed", description: message.payload.error, variant: "destructive" });
          setIsProcessing(false);
          ws.current?.close();
          break;
      }
    } catch (error) {
      console.error("Failed to parse WebSocket message:", error);
    }
  };

  const handleStartRecording = () => {
    const newClientId = uuidv4();
    setClientId(newClientId);
    setIsRecording(true);
    setGeneratedWorkflow(null);
    setCapturedEvents([]);
    setWorkflowNodes([]);
    setWorkflowEdges([]);
    setRecordingTime(0);

    // Setup WebSocket connection
    // The useWebSocket hook will pick up the new clientId via state change
    toast({
      title: "Recording",
      description: "Live session initiated.",
    });

    timerRef.current = setInterval(() => setRecordingTime(prev => prev + 1), 1000);

    // Simulate capturing events locally
    let eventIndex = 0;
    eventSimulatorRef.current = setInterval(() => {
      if (eventIndex < mockEventStream.length) {
        setCapturedEvents(prev => [...prev, { ...mockEventStream[eventIndex], timestamp: new Date().toISOString() }]);
        eventIndex++;
      } else {
        eventIndex = 0; // Loop for demo
      }
    }, 1200);
  };

  const handleStopRecording = () => {
    setIsRecording(false);
    setIsProcessing(true);
    clearInterval(timerRef.current);
    clearInterval(eventSimulatorRef.current);

    // Send captured events to the backend for analysis
    apiClient.analyzeRecording(clientId, capturedEvents, "User is processing an invoice.")
      .catch(error => {
        toast({ title: "Error starting analysis", description: error.message, variant: "destructive" });
        setIsProcessing(false);
      });
  };

  const handleSaveAndEdit = () => {
    if (!generatedWorkflow) return;
    createWorkflowMutation.mutate(generatedWorkflow);
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60).toString().padStart(2, '0');
    const secs = (seconds % 60).toString().padStart(2, '0');
    return `${mins}:${secs}`;
  };

  return (
    <div className="h-[calc(100vh-theme-header-height)] flex flex-col space-y-4">
      <div className="flex items-center justify-between space-y-2 p-4 border-b">
        <h1 className="text-3xl font-bold tracking-tight">Recording Studio</h1>
        <div className="flex items-center space-x-4">
          <StatusIndicator isRecording={isRecording} isProcessing={isProcessing} />
          <span className="text-lg font-mono">{formatTime(recordingTime)}</span>
          {!isRecording ? (
            <Button onClick={handleStartRecording} disabled={isProcessing}>
              <Circle className="mr-2 h-4 w-4 text-red-500 fill-current" />
              Start Recording
            </Button>
          ) : (
            <Button onClick={handleStopRecording} variant="destructive">
              <Square className="mr-2 h-4 w-4" />
              Stop Recording
            </Button>
          )}
          {generatedWorkflow && (
            <Button onClick={handleSaveAndEdit} disabled={createWorkflowMutation.isPending}>
              <Save className="mr-2 h-4 w-4" />
              {createWorkflowMutation.isPending ? "Saving..." : "Save & Edit Workflow"}
            </Button>
          )}
        </div>
      </div>
      
      <ResizablePanelGroup direction="horizontal" className="flex-grow">
        <ResizablePanel defaultSize={65}>
          <div className="h-full w-full bg-gray-200 relative">
            <VisualWorkflowEditor
              initialNodes={workflowNodes}
              initialEdges={workflowEdges}
              isReadOnly={true}
            />
            {!isRecording && workflowNodes.length === 0 && (
                <div className="absolute inset-0 flex items-center justify-center bg-gray-200/80">
                    <div className="text-center p-8 bg-white/90 rounded-lg shadow-lg">
                        <Bot className="h-12 w-12 mx-auto text-primary" />
                        <h2 className="mt-4 text-xl font-semibold">Ready to Automate?</h2>
                        <p className="mt-2 text-muted-foreground">Click "Start Recording" to begin capturing your process.</p>
                    </div>
                </div>
            )}
          </div>
        </ResizablePanel>
        <ResizableHandle withHandle />
        <ResizablePanel defaultSize={35}>
          <Tabs defaultValue="events" className="h-full flex flex-col">
            <TabsList className="mx-4 mt-2">
              <TabsTrigger value="events">Live Event Feed</TabsTrigger>
              <TabsTrigger value="details" disabled={!generatedWorkflow}>Workflow Details</TabsTrigger>
            </TabsList>
            <TabsContent value="events" className="flex-grow overflow-hidden">
              <EventFeed events={capturedEvents} />
            </TabsContent>
            <TabsContent value="details" className="p-4">
              {generatedWorkflow && (
                <div>
                  <h3 className="font-bold text-lg">{generatedWorkflow.name}</h3>
                  <p className="text-sm text-muted-foreground">{generatedWorkflow.description}</p>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  );
}
