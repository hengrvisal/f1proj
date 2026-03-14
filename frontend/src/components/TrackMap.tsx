"use client";

import { useEffect, useRef } from "react";
import * as d3 from "d3";
import { TelemetrySample } from "@/lib/api";

interface Props {
  samples: TelemetrySample[];
  colorBy?: "speed" | "throttle" | "gear";
  width?: number;
  height?: number;
}

export default function TrackMap({
  samples,
  colorBy = "speed",
  width = 400,
  height = 400,
}: Props) {
  const ref = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!ref.current || !samples.length) return;

    const points = samples.filter((s) => s.x != null && s.y != null);
    if (points.length < 10) return;

    const svg = d3.select(ref.current);
    svg.selectAll("*").remove();

    const margin = 30;
    const xExt = d3.extent(points, (d) => d.x!) as [number, number];
    const yExt = d3.extent(points, (d) => d.y!) as [number, number];

    const xScale = d3.scaleLinear().domain(xExt).range([margin, width - margin]);
    const yScale = d3.scaleLinear().domain(yExt).range([height - margin, margin]);

    let colorScale: d3.ScaleSequential<string>;
    let getValue: (d: TelemetrySample) => number;

    if (colorBy === "speed") {
      const ext = d3.extent(points, (d) => d.speed) as [number, number];
      colorScale = d3.scaleSequential(d3.interpolateTurbo).domain(ext);
      getValue = (d) => d.speed;
    } else if (colorBy === "throttle") {
      colorScale = d3.scaleSequential(d3.interpolateGreens).domain([0, 100]);
      getValue = (d) => d.throttle;
    } else {
      colorScale = d3.scaleSequential(d3.interpolateSpectral).domain([1, 8]);
      getValue = (d) => d.gear;
    }

    // Draw track segments
    for (let i = 0; i < points.length - 1; i++) {
      svg
        .append("line")
        .attr("x1", xScale(points[i].x!))
        .attr("y1", yScale(points[i].y!))
        .attr("x2", xScale(points[i + 1].x!))
        .attr("y2", yScale(points[i + 1].y!))
        .attr("stroke", colorScale(getValue(points[i])))
        .attr("stroke-width", 3)
        .attr("stroke-linecap", "round");
    }

    // Start/finish line
    svg
      .append("circle")
      .attr("cx", xScale(points[0].x!))
      .attr("cy", yScale(points[0].y!))
      .attr("r", 5)
      .attr("fill", "#E10600")
      .attr("stroke", "#fff")
      .attr("stroke-width", 1);
  }, [samples, colorBy, width, height]);

  return <svg ref={ref} width={width} height={height} />;
}
