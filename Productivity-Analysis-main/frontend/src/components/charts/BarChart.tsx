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
      textStyle: { fontSize: 13, color: '#e2e8f0' }
    },
    tooltip: { trigger: 'axis', formatter: '{b}: <b>{c}%</b>' },
    grid: { left: '3%', right: '4%', bottom: '15%', top: '20%', containLabel: true },
    xAxis: {
      type: 'category',
      data: names,
      axisLabel: { rotate: 25, fontSize: 10, color: '#94a3b8' }
    },
    yAxis: {
      type: 'value',
      max: 100,
      axisLabel: { formatter: '{value}%', color: '#94a3b8' },
      splitLine: { lineStyle: { color: '#1e293b' } }
    },
    series: [
      {
        data: values,
        type: 'bar',
        itemStyle: {
          color: '#38bdf8',
          borderRadius: [4, 4, 0, 0]
        }
      }
    ]
  };

  return <ReactECharts option={options} style={{ height, width: '100%' }} notMerge={true} lazyUpdate={true} />;
};
