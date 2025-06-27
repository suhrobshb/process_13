import React, { useEffect } from 'react';

/**
 * Custom ReactFlow edge used in the WorkflowEditor.
 * ------------------------------------------------
 * Props (injected by ReactFlow):
 *   id, sourceX, sourceY, targetX, targetY,
 *   selected, data (user-defined object)
 *
 * Edge `data` can include:
 *   - status  : 'default' | 'success' | 'warning' | 'error'
 *   - active  : boolean  → if true the edge is animated
 */

export function FlowConnector({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  selected,
  data = {},
}) {
  // ---- Styling helpers ----------------------------------------------------
  const status = data.status || 'default';
  const colorMap = {
    default: '#9ca3af', // gray-400
    success: '#22c55e', // green-500
    warning: '#fbbf24', // yellow-400
    error: '#ef4444', // red-500
  };

  const stroke = colorMap[status] ?? colorMap.default;
  const animated = Boolean(data.active);

  // Inject a tiny stylesheet once for the dash animation.
  useEffect(() => {
    if (document.getElementById('flow-edge-style')) return;
    const style = document.createElement('style');
    style.id = 'flow-edge-style';
    style.textContent = `
      @keyframes dash {
        to {
          stroke-dashoffset: -1000;
        }
      }
    `;
    document.head.appendChild(style);
  }, []);

  // ---- SVG Path -----------------------------------------------------------
  const markerId = `arrow-${id}`;

  return (
    <g className="flow-connector">
      {/* Arrow definition */}
      <defs>
        <marker
          id={markerId}
          markerWidth="10"
          markerHeight="10"
          refX="10"
          refY="5"
          orient="auto"
          markerUnits="strokeWidth"
        >
          <path d="M 0 0 L 10 5 L 0 10 z" fill={stroke} />
        </marker>
      </defs>

      {/* Main line */}
      <line
        x1={sourceX}
        y1={sourceY}
        x2={targetX}
        y2={targetY}
        stroke={stroke}
        strokeWidth={selected ? 3 : 2}
        markerEnd={`url(#${markerId})`}
        strokeDasharray={animated ? '6 4' : undefined}
        style={
          animated
            ? {
                animation: 'dash 1s linear infinite',
                strokeDashoffset: 0,
              }
            : undefined
        }
      />
    </g>
  );
}
