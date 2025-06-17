import React from 'react';

export function StepBox({ step, onEdit, onDelete }) {
  return (
    <div className="step-box p-4 rounded shadow bg-white">
      <h4>{step.name}</h4>
      <button onClick={() => onEdit(step.id)}>Edit</button>
      <button onClick={() => onDelete(step.id)}>Delete</button>
    </div>
  );
}
