import React from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine
} from 'recharts';

interface ProsodyPoint {
  t_ms: number;
  f0_hz: number | null;
  rms_db: number;
  voiced: boolean;
}

interface ProsodyChartProps {
  data: ProsodyPoint[];
  medianF0?: number;
  p10F0?: number;
  p90F0?: number;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    const timeSec = (label / 1000).toFixed(1);
    return (
      <div className="bg-white border p-2 shadow rounded text-xs">
        <p className="font-semibold">{`${timeSec}s`}</p>
        {payload.map((entry: any, index: number) => (
          <p key={index} style={{ color: entry.color }}>
            {`${entry.name}: ${entry.value !== null ? entry.value.toFixed(1) : 'Unvoiced'} ${entry.name === 'Pitch' ? 'Hz' : 'dB'}`}
          </p>
        ))}
      </div>
    );
  }
  return null;
};

export const ProsodyChart: React.FC<ProsodyChartProps> = ({ data, medianF0, p10F0, p90F0 }) => {
  // Filter for visualization (don't try to render thousands of points if not necessary)
  // For now, we assume data is already bucketed/downsampled reasonably
  
  if (!data || data.length === 0) {
    return <div className="text-gray-500 text-sm italic">No prosody data available for this segment.</div>;
  }

  return (
    <div className="w-full h-64 mt-4">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={data}
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
          <XAxis 
            dataKey="t_ms" 
            tickFormatter={(tick) => `${(tick / 1000).toFixed(1)}s`}
            minTickGap={30}
            style={{ fontSize: '10px' }}
          />
          <YAxis 
            yAxisId="left" 
            label={{ value: 'Pitch (Hz)', angle: -90, position: 'insideLeft', style: { fontSize: '12px' } }}
            domain={['auto', 'auto']}
            style={{ fontSize: '10px' }}
          />
          <YAxis 
            yAxisId="right" 
            orientation="right" 
            label={{ value: 'Energy (dB)', angle: 90, position: 'insideRight', style: { fontSize: '12px' } }}
            domain={['auto', 'auto']}
            style={{ fontSize: '10px' }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ fontSize: '12px' }} />
          
          {/* F0 Line (only connects voiced points implicitly because nulls break the line in recharts by default) */}
          <Line 
            yAxisId="left" 
            type="monotone" 
            dataKey="f0_hz" 
            name="Pitch" 
            stroke="#8b5cf6" 
            dot={false}
            connectNulls={false}
            strokeWidth={2}
          />
          
          {/* Energy Line */}
          <Line 
            yAxisId="right" 
            type="monotone" 
            dataKey="rms_db" 
            name="Energy" 
            stroke="#f59e0b" 
            dot={false}
            strokeWidth={1.5}
            opacity={0.7}
          />
          
          {medianF0 && (
            <ReferenceLine yAxisId="left" y={medianF0} stroke="#8b5cf6" strokeDasharray="3 3" opacity={0.5} label={{ position: 'insideTopLeft', value: 'Median F0', fill: '#8b5cf6', fontSize: 10 }} />
          )}
          {p90F0 && (
             <ReferenceLine yAxisId="left" y={p90F0} stroke="#cbd5e1" strokeDasharray="1 1" opacity={0.5} />
          )}
          {p10F0 && (
             <ReferenceLine yAxisId="left" y={p10F0} stroke="#cbd5e1" strokeDasharray="1 1" opacity={0.5} />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};
