import React from 'react';

export function ApprovalBox({ step, onToggle }) {
  return (
    <div className="approval-box p-3 bg-yellow-50 rounded">
      <label>
        <input
          type="checkbox"
          checked={step.requiresApproval}
          onChange={() => onToggle(step.id)}
        /> Require approval
      </label>
    </div>
  );
}
