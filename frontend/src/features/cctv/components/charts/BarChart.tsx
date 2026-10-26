import React from 'react';
import ReactECharts from 'echarts-for-react';
import type { SpatialZone } from '../../types';

interface BarChartProps {
  zones: SpatialZone[];
  height?: string;
}

export const BarChart: React.FC<BarChartProps> = ({ zones, height = '300px' }) => {
  const names = zones.map((z, idx) => z.zone_id || `Z-${idx}`);
  const values = zones.map((z) => {
    const ztype = z.zone_type || 'WORKSTATION';
    if (ztype === 'WORKSTATION') return 78.5;
    if (ztype === 'COLLABORATION') return 62.0;
    if (ztype === 'CORRIDOR') return 15.2;
    return 45.0;
  });

  const options = {
    backgroundColor: 'transparent',
    title: {
      text: 'Zone Utilization Rates',
      left: 'center',
      textStyle: { fontSize: 13, fontWeight: 600, color: '#334155' }
    },
    tooltip: { trigger: 'axis', formatter: '{b}: <b>{c}%</b>' },
    grid: { left: '3%', right: '4%', bottom: '15%', top: '20%', containLabel: true },
    xAxis: {
      type: 'category',
      data: names,
      axisLabel: { rotate: 25, fontSize: 10, color: '#64748b' }
    },
    yAxis: {
      type: 'value',
      max: 100,
      axisLabel: { formatter: '{value}%', color: '#64748b' },
      splitLine: { lineStyle: { color: '#f1f5f9' } }
    },
    series: [
      {
        data: values,
        type: 'bar',
        itemStyle: {
          color: '#2563eb',
          borderRadius: [4, 4, 0, 0]
        }
      }
    ]
  };

  return <ReactECharts option={options} style={{ height, width: '100%' }} notMerge={true} lazyUpdate={true} />;
};
