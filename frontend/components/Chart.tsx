"use client";
import { ResponsiveContainer } from "recharts";
/** Charts always lay out left-to-right (time axes keep their meaning); labels inside still render Arabic text. */
export const ChartBox = ({ h = 260, children }: { h?: number; children: React.ReactElement }) => <div className="chart-ltr" style={{ width: "100%", height: h }}><ResponsiveContainer width="100%" height="100%">{children}</ResponsiveContainer></div>;
export const axis = { fontSize: 11, fill: "var(--chart-axis)" };
