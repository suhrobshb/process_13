import React from "react";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

/**
 * A specialized panel for configuring LLM-specific parameters within the
 * properties panel.
 */
const LLMProcessConfig = ({ processData, onProcessChange }) => {
  return (
    <div className="space-y-4 mt-4 p-4 border rounded-md bg-muted/50">
      <h4 className="font-semibold text-sm">LLM Configuration</h4>
      <div>
        <label className="text-xs font-medium text-muted-foreground">Provider</label>
        <Select
          value={processData.provider || 'openai'}
          onValueChange={(value) => onProcessChange('provider', value)}
        >
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="openai">OpenAI</SelectItem>
            <SelectItem value="anthropic">Anthropic</SelectItem>
            <SelectItem value="local">Local (Ollama)</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div>
        <label className="text-xs font-medium text-muted-foreground">Model</label>
        <Input
          value={processData.model || ''}
          onChange={(e) => onProcessChange('model', e.target.value)}
          placeholder="e.g., gpt-4-turbo"
        />
      </div>
      <div>
        <label className="text-xs font-medium text-muted-foreground">Prompt Template</label>
        <Textarea
          value={processData.prompt || ''}
          onChange={(e) => onProcessChange('prompt', e.target.value)}
          placeholder="Summarize the following text: {{ previous_step.output.text }}"
          rows={6}
        />
        <p className="text-xs text-muted-foreground mt-1">
          Use `{{variable_name}}` to insert data from previous steps.
        </p>
      </div>
    </div>
  );
};

/**
 * NodePropertiesPanel
 * ===================
 * A UI component that displays an editor for the properties of a selected
 * workflow node. It provides a clear, structured interface for editing the
 * Input, Process, and Output (IPO) stages of a step.
 *
 * @param {object} props - The component props.
 * @param {object} props.node - The currently selected workflow node object.
 * @param {function} props.onChange - A callback function to update the node's data.
 */
export function NodePropertiesPanel({ node, onChange }) {
  if (!node) {
    return (
      <div className="p-8 text-center text-muted-foreground">
        <p>Select a node to view and edit its properties.</p>
      </div>
    );
  }

  // Generic handler to update nested properties in the node's data.
  // path: e.g., "process.type" or "input.source"
  const handleNestedChange = (path, value) => {
    const keys = path.split('.');
    const newStepData = { ...node };

    let current = newStepData;
    for (let i = 0; i < keys.length - 1; i++) {
      current = current[keys[i]] = { ...current[keys[i]] };
    }
    current[keys[keys.length - 1]] = value;
    
    onChange(newStepData);
  };
  
  return (
    <div className="p-4 space-y-6 overflow-y-auto h-full">
      <div>
        <h2 className="text-lg font-bold">Step: {node.name}</h2>
        <p className="text-sm text-muted-foreground">ID: {node.id}</p>
      </div>
      
      <Separator />

      {/* --- INPUT SECTION --- */}
      <Card>
        <CardHeader>
          <CardTitle>1. Input</CardTitle>
          <p className="text-sm text-muted-foreground">
            Define the data this step requires to run.
          </p>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <label className="text-sm font-medium">Input Source Description</label>
            <Textarea
              value={node.input?.description || ''}
              onChange={(e) => handleNestedChange('input.description', e.target.value)}
              placeholder="e.g., 'Receives the attached PDF from the trigger email.' or 'Uses the 'extracted_text' variable from the previous step.'"
              rows={3}
            />
          </div>
        </CardContent>
      </Card>

      {/* --- PROCESS SECTION --- */}
      <Card>
        <CardHeader>
          <CardTitle>2. Process</CardTitle>
           <p className="text-sm text-muted-foreground">
            Configure the action to be performed.
          </p>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">Action Type</label>
              <Select
                value={node.process?.type || 'desktop'}
                onValueChange={(value) => handleNestedChange('process.type', value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select an action type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="desktop">Desktop Automation</SelectItem>
                  <SelectItem value="browser">Browser Automation</SelectItem>
                  <SelectItem value="llm">LLM Processing</SelectItem>
                  <SelectItem value="shell">Shell Command</SelectItem>
                  <SelectItem value="http">HTTP Request</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
                <label className="text-sm font-medium">Process Description</label>
                <Textarea
                  value={node.process?.description || ''}
                  onChange={(e) => handleNestedChange('process.description', e.target.value)}
                  placeholder="A human-readable summary of what this step does."
                  rows={3}
                />
            </div>

            {/* Conditional configuration based on process type */}
            {node.process?.type === 'llm' && (
              <LLMProcessConfig 
                processData={node.process}
                onProcessChange={(field, value) => handleNestedChange(`process.${field}`, value)}
              />
            )}
            {/* TODO: Add specific config panels for 'desktop', 'browser', etc. */}

          </div>
        </CardContent>
      </Card>

      {/* --- OUTPUT SECTION --- */}
      <Card>
        <CardHeader>
          <CardTitle>3. Output</CardTitle>
          <p className="text-sm text-muted-foreground">
            Describe the expected result of this step.
          </p>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <label className="text-sm font-medium">Output Variable Name</label>
            <Input
              value={node.output?.variable || ''}
              onChange={(e) => handleNestedChange('output.variable', e.target.value)}
              placeholder="e.g., 'invoice_data' or 'confirmation_id'"
            />
             <p className="text-xs text-muted-foreground mt-1">
              This variable can be used by subsequent steps.
            </p>
          </div>
           <div className="space-y-2 mt-4">
            <label className="text-sm font-medium">Output Description</label>
            <Textarea
              value={node.output?.description || ''}
              onChange={(e) => handleNestedChange('output.description', e.target.value)}
              placeholder="e.g., 'A JSON object containing the extracted invoice details.' or 'The confirmation number from the web portal.'"
              rows={3}
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
