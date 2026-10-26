import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';

interface FeatureDataPoint {
  timestamp_ms: number;
  value: number;
}

interface FeatureChartProps {
  data: FeatureDataPoint[];
  metricName?: string;
}

export default function FeatureChart({ data, metricName = 'Value' }: FeatureChartProps) {
  // Format the timestamp for the X-axis (convert ms to seconds for readability if needed)
  const formattedData = data.map(d => ({
    ...d,
    timeSec: (d.timestamp_ms / 1000).toFixed(1)
  }));

  return (
    <div className="w-full h-64 bg-white p-4 rounded shadow-sm">
      <h3 className="text-lg font-semibold mb-4">{metricName} Over Time</h3>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={formattedData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
          <Line type="monotone" dataKey="value" stroke="#8884d8" dot={false} isAnimationActive={false} />
          <CartesianGrid stroke="#ccc" strokeDasharray="5 5" />
          <XAxis 
            dataKey="timeSec" 
            label={{ value: 'Time (s)', position: 'insideBottomRight', offset: -5 }} 
          />
          <YAxis />
          <Tooltip 
            labelFormatter={(label) => `Time: ${label}s`} 
            formatter={(value: any) => [value, metricName]}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
