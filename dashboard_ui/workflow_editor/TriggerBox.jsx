import React from 'react';

export function TriggerBox({ trigger, onEdit }) {
  return (
    <div className="trigger-box p-3 bg-green-50 rounded">
      <p><strong>Trigger:</strong> {trigger.type} – {trigger.spec}</p>
      <button onClick={() => onEdit(trigger.id)}>Edit Trigger</button>
    </div>
  );
}
