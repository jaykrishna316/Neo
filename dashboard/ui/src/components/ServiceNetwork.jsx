import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import '../styles/components.css';

function ServiceNetwork({ data, onRefresh }) {
  const svgRef = useRef();

  useEffect(() => {
    if (!data || !data.nodes || !data.links || !svgRef.current) return;

    const width = svgRef.current.clientWidth;
    const height = 500;

    // Clear previous
    d3.select(svgRef.current).selectAll('*').remove();

    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height);

    // Create simulation
    const simulation = d3.forceSimulation(data.nodes)
      .force('link', d3.forceLink(data.links).id(d => d.id).distance(100))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2));

    // Add links
    const link = svg.append('g')
      .selectAll('line')
      .data(data.links)
      .join('line')
      .attr('stroke', d => d.color || '#666')
      .attr('stroke-width', 2)
      .attr('opacity', 0.6);

    // Add nodes
    const node = svg.append('g')
      .selectAll('g')
      .data(data.nodes)
      .join('g')
      .call(drag(simulation));

    node.append('circle')
      .attr('r', 25)
      .attr('fill', '#06b6d4')
      .attr('opacity', 0.8)
      .attr('stroke', '#0f172a')
      .attr('stroke-width', 2);

    node.append('text')
      .text(d => d.id.substring(0, 3).toUpperCase())
      .attr('text-anchor', 'middle')
      .attr('dy', '0.3em')
      .attr('fill', '#f1f5f9')
      .attr('font-size', '12px')
      .attr('font-weight', 'bold')
      .attr('pointer-events', 'none');

    // Update positions on simulation tick
    simulation.on('tick', () => {
      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);

      node.attr('transform', d => `translate(${d.x},${d.y})`);
    });

    return () => simulation.stop();
  }, [data]);

  function drag(simulation) {
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

    return d3.drag()
      .on('start', dragstarted)
      .on('drag', dragged)
      .on('end', dragended);
  }

  return (
    <div className="component-card">
      <div className="cell-header">
        <h3 className="cell-title">🕸️ Service Coupling Network</h3>
        <button className="btn-small" onClick={onRefresh}>🔄</button>
      </div>
      <svg ref={svgRef} className="network-svg"></svg>
      <p className="network-info">
        Drag nodes to explore. Color indicates coupling strength: 🟢 Low → 🔴 High
      </p>
    </div>
  );
}

export default ServiceNetwork;
