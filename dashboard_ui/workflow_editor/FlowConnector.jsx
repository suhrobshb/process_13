import React from 'react';

export function FlowConnector({ fromId, toId }) {
  return (
    <svg className="flow-connector">
      <line id={`${fromId}-${toId}`} /* TODO: compute coords */ />
    </svg>
  );
}
