import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

/**
 * TaskRelationshipGraph
 * ---------------------
 * Renders a simple force-directed graph using D3.
 *
 * Props:
 *   – graphData OR clusters: {
 *       nodes: [{ id, label } ...],
 *       links: [{ source, target } ...]
 *     }
 *
 * If the dashboard passes `clusters` (current behaviour) we fall back to that.
 */
export function TaskRelationshipGraph({ graphData, clusters }) {
  const svgRef = useRef(null);

  // Prefer graphData; fallback to clusters (keeps backwards-compat with dashboard)
  const data = graphData || clusters;

  // Render / update graph
  useEffect(() => {
    const svgEl = d3.select(svgRef.current);
    // Clear old contents on each render
    svgEl.selectAll('*').remove();

    if (!data || !data.nodes || data.nodes.length === 0) {
      // Display a friendly message when there is no graph data
      svgEl
        .append('text')
        .attr('x', 300)
        .attr('y', 200)
        .attr('text-anchor', 'middle')
        .attr('fill', '#999')
        .text('No data to display');
      return;
    }

    const width = +svgEl.attr('width');
    const height = +svgEl.attr('height');

    // Create simulation
    const simulation = d3
      .forceSimulation(data.nodes)
      .force('link', d3.forceLink(data.links).id((d) => d.id).distance(100))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2));

    // Draw links
    const link = svgEl
      .append('g')
      .attr('stroke', '#aaa')
      .attr('stroke-width', 1.5)
      .selectAll('line')
      .data(data.links)
      .enter()
      .append('line');

    // Draw nodes
    const node = svgEl
      .append('g')
      .attr('stroke', '#fff')
      .attr('stroke-width', 1.5)
      .selectAll('circle')
      .data(data.nodes)
      .enter()
      .append('circle')
      .attr('r', 8)
      .attr('fill', '#4285F4')
      .call(
        d3
          .drag()
          .on('start', dragstarted)
          .on('drag', dragged)
          .on('end', dragended)
      );

    // Optional labels
    svgEl
      .append('g')
      .selectAll('text')
      .data(data.nodes)
      .enter()
      .append('text')
      .text((d) => d.label || d.id)
      .attr('font-size', 10)
      .attr('dx', 12)
      .attr('dy', '.35em');

    // Tick handler
    simulation.on('tick', () => {
      link
        .attr('x1', (d) => d.source.x)
        .attr('y1', (d) => d.source.y)
        .attr('x2', (d) => d.target.x)
        .attr('y2', (d) => d.target.y);

      node.attr('cx', (d) => d.x).attr('cy', (d) => d.y);

      svgEl
        .selectAll('text')
        .attr('x', (d) => d.x)
        .attr('y', (d) => d.y);
    });

    // Clean-up on unmount or data change
    return () => simulation.stop();

    // ---- drag handlers ----
    function dragstarted(event, d) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }
    function dragged(event, d) {
      d.fx = event.x;
      d.fy = event.y;
    }
    function dragended(event, d) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }
  }, [data]);

  return <svg ref={svgRef} width="600" height="400" />;
