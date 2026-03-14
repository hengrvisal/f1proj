"use client";

import { useEffect, useRef } from "react";
import * as d3 from "d3";
import { SimilarityMatrix } from "@/lib/api";

interface Props {
  data: SimilarityMatrix;
}

export default function SimilarityHeatmap({ data }: Props) {
  const ref = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!ref.current || !data.drivers.length) return;

    const drivers = data.drivers;
    const n = drivers.length;
    const cellSize = Math.min(32, 600 / n);
    const margin = { top: 80, right: 20, bottom: 20, left: 80 };
    const width = n * cellSize;
    const height = n * cellSize;

    const svg = d3.select(ref.current);
    svg.selectAll("*").remove();
    svg.attr("width", width + margin.left + margin.right);
    svg.attr("height", height + margin.top + margin.bottom);

    const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

    const color = d3
      .scaleSequential(d3.interpolateRdYlGn)
      .domain([-0.5, 1]);

    // Cells
    for (let i = 0; i < n; i++) {
      for (let j = 0; j < n; j++) {
        const sim = data.matrix[drivers[i]]?.[drivers[j]] ?? (i === j ? 1 : 0);
        g.append("rect")
          .attr("x", j * cellSize)
          .attr("y", i * cellSize)
          .attr("width", cellSize - 1)
          .attr("height", cellSize - 1)
          .attr("fill", color(sim))
          .attr("rx", 2)
          .append("title")
          .text(`${drivers[i]} vs ${drivers[j]}: ${sim.toFixed(3)}`);
      }
    }

    // X labels
    g.selectAll(".x-label")
      .data(drivers)
      .join("text")
      .attr("class", "x-label")
      .attr("x", (_, i) => i * cellSize + cellSize / 2)
      .attr("y", -8)
      .attr("text-anchor", "start")
      .attr("transform", (_, i) => `rotate(-45, ${i * cellSize + cellSize / 2}, -8)`)
      .attr("fill", "#888899")
      .attr("font-size", Math.min(11, cellSize - 2))
      .text((d) => d);

    // Y labels
    g.selectAll(".y-label")
      .data(drivers)
      .join("text")
      .attr("class", "y-label")
      .attr("x", -8)
      .attr("y", (_, i) => i * cellSize + cellSize / 2 + 4)
      .attr("text-anchor", "end")
      .attr("fill", "#888899")
      .attr("font-size", Math.min(11, cellSize - 2))
      .text((d) => d);
  }, [data]);

  return (
    <div className="overflow-x-auto">
      <svg ref={ref} />
    </div>
  );
}
