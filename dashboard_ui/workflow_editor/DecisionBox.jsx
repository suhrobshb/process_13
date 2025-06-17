import React from 'react';

export function DecisionBox({ decision, onEdit }) {
  return (
    <div className="decision-box p-3 bg-blue-50 rounded">
      <p><strong>Decision:</strong> {decision.rule}</p>
      <button onClick={() => onEdit(decision.id)}>Edit Decision</button>
    </div>
  );
}
