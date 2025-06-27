import React from 'react';
import { Handle, Position } from 'reactflow';

/**
 * StepBox – custom React Flow node.
 *
 * Props (injected by ReactFlow):
 *   data: {
 *     label: string,
 *     status?: 'completed' | 'processing' | 'error' | 'pending'
 *   }
 *   selected: boolean
 */
export function StepBox({ data, selected }) {
  const { label = 'Step', status = 'pending' } = data ?? {};

  const statusColor =
    {
      completed: 'bg-green-500',
      processing: 'bg-yellow-500',
      error: 'bg-red-500',
      pending: 'bg-gray-400',
    }[status] || 'bg-gray-400';

  return (
    <div
      className={`step-box min-w-[120px] text-sm px-4 py-3 rounded shadow-md bg-white border
        ${selected ? 'border-blue-500' : 'border-gray-200'}`}
    >
      {/* ReactFlow handles */}
      <Handle
        type="target"
        position={Position.Top}
        id="in"
        style={{ background: '#555' }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="out"
        style={{ background: '#555' }}
      />

      {/* Node content */}
      <div className="flex items-center gap-2">
        <span
          className={`inline-block w-2 h-2 rounded-full ${statusColor}`}
          title={status}
        />
        <span className="font-medium">{label}</span>
      </div>
    </div>
  );
}
