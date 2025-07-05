import React from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/use-toast";
import { Loader2, Save, Key, User, Settings as SettingsIcon, GitFork } from "lucide-react";
import { apiClient } from "@/lib/api-client";
import { Separator } from "@/components/ui/separator";

// --- Zod Schemas for Form Validation ---

const profileFormSchema = z.object({
  fullName: z.string().min(2, "Full name must be at least 2 characters."),
  email: z.string().email("Please enter a valid email address."),
  theme: z.enum(["light", "dark", "system"]),
  emailNotifications: z.boolean(),
});
type ProfileFormData = z.infer<typeof profileFormSchema>;

const apiKeysFormSchema = z.object({
  openaiApiKey: z.string().refine(val => val === '' || val.startsWith("sk-"), "Must be a valid OpenAI API key or empty."),
});
type ApiKeysFormData = z.infer<typeof apiKeysFormSchema>;

const systemSettingsFormSchema = z.object({
  allowUserRegistration: z.boolean(),
  defaultUserRole: z.enum(["viewer", "editor"]),
});
type SystemSettingsFormData = z.infer<typeof systemSettingsFormSchema>;

const workflowDefaultsSchema = z.object({
    defaultConfidenceThreshold: z.number().min(0).max(1),
    maxExecutionRetries: z.number().int().min(0).max(10),
});
type WorkflowDefaultsFormData = z.infer<typeof workflowDefaultsSchema>;


// --- Mock API Functions ---
// Replace these with actual apiClient calls when the backend is ready.

const fetchSettings = async () => {
  await new Promise(resolve => setTimeout(resolve, 500));
  return {
    profile: { fullName: "Demo User", email: "user@example.com", theme: "system", emailNotifications: true },
    apiKeys: { openaiApiKey: "sk-..." },
    system: { allowUserRegistration: true, defaultUserRole: "editor" },
    workflows: { defaultConfidenceThreshold: 0.85, maxExecutionRetries: 3 },
  };
};

const updateSettings = async (data: any) => {
  await new Promise(resolve => setTimeout(resolve, 1000));
  console.log("Settings updated:", data);
  return { success: true };
};


// --- Form Components for Each Tab ---

const ProfileForm = ({ data }) => {
  const { toast } = useToast();
  const mutation = useMutation({ mutationFn: updateSettings, onSuccess: () => toast({ title: "Profile updated successfully!" }) });
  const { control, handleSubmit } = useForm<ProfileFormData>({
    resolver: zodResolver(profileFormSchema),
    defaultValues: data,
  });
  const onSubmit = (formData: ProfileFormData) => mutation.mutate({ profile: formData });

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <div className="space-y-2">
        <label htmlFor="fullName">Full Name</label>
        <Controller name="fullName" control={control} render={({ field }) => <Input id="fullName" {...field} />} />
      </div>
      <div className="space-y-2">
        <label htmlFor="email">Email</label>
        <Controller name="email" control={control} render={({ field }) => <Input id="email" type="email" {...field} />} />
      </div>
      <Separator />
      <div className="space-y-2">
        <label htmlFor="theme">Theme</label>
        <Controller name="theme" control={control} render={({ field }) => (
          <Select onValueChange={field.onChange} value={field.value}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="light">Light</SelectItem>
              <SelectItem value="dark">Dark</SelectItem>
              <SelectItem value="system">System</SelectItem>
            </SelectContent>
          </Select>
        )} />
      </div>
      <div className="flex items-center justify-between rounded-lg border p-4">
        <div className="space-y-0.5">
          <label>Email Notifications</label>
          <p className="text-sm text-muted-foreground">Receive notifications about workflow failures and approvals.</p>
        </div>
        <Controller name="emailNotifications" control={control} render={({ field }) => <Switch checked={field.value} onCheckedChange={field.onChange} />} />
      </div>
      <Button type="submit" disabled={mutation.isPending}>
        {mutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        Save Preferences
      </Button>
    </form>
  );
};

const ApiKeysForm = ({ data }) => {
    const { toast } = useToast();
    const mutation = useMutation({ mutationFn: updateSettings, onSuccess: () => toast({ title: "API Keys updated!" }) });
    const { control, handleSubmit } = useForm<ApiKeysFormData>({
      resolver: zodResolver(apiKeysFormSchema),
      defaultValues: data,
    });
    const onSubmit = (formData: ApiKeysFormData) => mutation.mutate({ apiKeys: formData });
  
    return (
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <div className="space-y-2">
          <label htmlFor="openaiApiKey">OpenAI API Key</label>
          <Controller name="openaiApiKey" control={control} render={({ field }) => <Input id="openaiApiKey" type="password" {...field} />} />
          <p className="text-xs text-muted-foreground">Used for LLM-powered steps. Your key is securely stored and never exposed to the client.</p>
        </div>
        <Button type="submit" disabled={mutation.isPending}>
          {mutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Save API Keys
        </Button>
      </form>
    );
};

// ... Implement SystemSettingsForm and WorkflowDefaultsForm similarly

// --- Main Settings Page Component ---

export default function SettingsPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["settings"],
    queryFn: fetchSettings,
  });

  if (isLoading) return <div className="flex justify-center items-center h-full"><Loader2 className="h-8 w-8 animate-spin" /></div>;
  if (isError) return <div className="text-red-500">Failed to load settings.</div>;

  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
      
      <Tabs defaultValue="profile" className="space-y-4">
        <TabsList>
          <TabsTrigger value="profile"><User className="mr-2 h-4 w-4" />Profile & Preferences</TabsTrigger>
          <TabsTrigger value="apiKeys"><Key className="mr-2 h-4 w-4" />API Keys</TabsTrigger>
          <TabsTrigger value="system"><SettingsIcon className="mr-2 h-4 w-4" />System</TabsTrigger>
          <TabsTrigger value="workflows"><GitFork className="mr-2 h-4 w-4" />Workflows</TabsTrigger>
        </TabsList>

        <TabsContent value="profile">
          <Card>
            <CardHeader>
              <CardTitle>Profile</CardTitle>
              <CardDescription>Manage your personal information and application preferences.</CardDescription>
            </CardHeader>
            <CardContent>
              <ProfileForm data={data.profile} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="apiKeys">
          <Card>
            <CardHeader>
              <CardTitle>API Keys</CardTitle>
              <CardDescription>Manage your API keys for third-party integrations.</CardDescription>
            </CardHeader>
            <CardContent>
                <ApiKeysForm data={data.apiKeys} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="system">
            <Card>
                <CardHeader>
                    <CardTitle>System Settings</CardTitle>
                    <CardDescription>Manage platform-wide settings (Admin only).</CardDescription>
                </CardHeader>
                <CardContent>
                    {/* Placeholder for SystemSettingsForm */}
                    <p>System settings form will be implemented here.</p>
                </CardContent>
            </Card>
        </TabsContent>

        <TabsContent value="workflows">
            <Card>
                <CardHeader>
                    <CardTitle>Workflow Defaults</CardTitle>
                    <CardDescription>Set default parameters for new workflows.</CardDescription>
                </CardHeader>
                <CardContent>
                    {/* Placeholder for WorkflowDefaultsForm */}
                    <p>Workflow defaults form will be implemented here.</p>
                </CardContent>
            </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
