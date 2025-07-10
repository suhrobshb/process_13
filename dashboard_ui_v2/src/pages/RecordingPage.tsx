import { RecordingStudio } from "@/components/recording/RecordingStudio";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  Zap, 
  BookOpen, 
  Settings, 
  HelpCircle 
} from "lucide-react";

// --- Main Recording Page Component ---

export default function RecordingPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Recording Studio</h1>
          <p className="text-muted-foreground">
            Capture and record your workflow processes in real-time
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button variant="outline">
            <Settings className="mr-2 h-4 w-4" />
            Settings
          </Button>
          <Button variant="outline">
            <HelpCircle className="mr-2 h-4 w-4" />
            Help
          </Button>
        </div>
      </div>

      <Tabs defaultValue="recording" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="recording">Recording Studio</TabsTrigger>
          <TabsTrigger value="templates">Templates</TabsTrigger>
          <TabsTrigger value="guide">Getting Started</TabsTrigger>
        </TabsList>

        <TabsContent value="recording" className="space-y-6">
          <RecordingStudio />
        </TabsContent>

        <TabsContent value="templates" className="space-y-6">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="h-5 w-5" />
                  Invoice Processing
                </CardTitle>
                <CardDescription>
                  Automated invoice data extraction and processing
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button variant="outline" className="w-full">
                  Use Template
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BookOpen className="h-5 w-5" />
                  Email Management
                </CardTitle>
                <CardDescription>
                  Automated email sorting and response workflows
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button variant="outline" className="w-full">
                  Use Template
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="h-5 w-5" />
                  Data Entry
                </CardTitle>
                <CardDescription>
                  Automated form filling and data validation
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button variant="outline" className="w-full">
                  Use Template
                </Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="guide" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Getting Started with Recording</CardTitle>
              <CardDescription>
                Learn how to capture and automate your workflows
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <h3 className="font-semibold">1. Prepare Your Workspace</h3>
                <p className="text-sm text-muted-foreground">
                  Close unnecessary applications and arrange your windows for optimal recording.
                </p>
              </div>
              <div className="space-y-2">
                <h3 className="font-semibold">2. Start Recording</h3>
                <p className="text-sm text-muted-foreground">
                  Click the record button and perform your workflow at normal speed.
                </p>
              </div>
              <div className="space-y-2">
                <h3 className="font-semibold">3. Review and Edit</h3>
                <p className="text-sm text-muted-foreground">
                  Review captured events and make adjustments before saving your workflow.
                </p>
              </div>
              <div className="space-y-2">
                <h3 className="font-semibold">4. Test and Deploy</h3>
                <p className="text-sm text-muted-foreground">
                  Test your workflow in a safe environment before scheduling regular execution.
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
