import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

export function TaskRelationshipGraph({ graphData }) {
  const ref = useRef();

  useEffect(() => {
    // TODO: render D3 force-directed graph
  }, [graphData]);

  return <svg ref={ref} width="600" height="400"></svg>;
}
