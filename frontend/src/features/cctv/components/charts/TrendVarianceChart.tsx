import React from 'react';
import ReactECharts from 'echarts-for-react';

interface TrendVarianceChartProps {
  hours: string[];
  occupancyRates: number[];
  title?: string;
  height?: string;
}

export const TrendVarianceChart: React.FC<TrendVarianceChartProps> = ({
  hours,
  occupancyRates,
  title = 'Hourly Workstation Occupancy Trend',
  height = '300px'
}) => {
  const upper = occupancyRates.map((v) => Math.min(100.0, v + 8.5));
  const lower = occupancyRates.map((v) => Math.max(0.0, v - 8.5));

  const options = {
    backgroundColor: 'transparent',
    title: { text: title, left: 'center', textStyle: { fontSize: 13, color: '#1e293b', fontWeight: 600 } },
    tooltip: { trigger: 'axis' },
    legend: {
      top: '8%',
      data: ['Mean Occupancy', 'Variance Band (±1σ)'],
      textStyle: { color: '#475569', fontSize: 11 }
    },
    grid: { left: '3%', right: '4%', bottom: '10%', top: '25%', containLabel: true },
    xAxis: {
      type: 'category',
      data: hours,
      boundaryGap: false,
      axisLabel: { color: '#64748b' }
    },
    yAxis: {
      type: 'value',
      max: 100,
      axisLabel: { formatter: '{value}%', color: '#64748b' },
      splitLine: { lineStyle: { color: '#e2e8f0' } }
    },
    series: [
      {
        name: 'Mean Occupancy',
        type: 'line',
        data: occupancyRates,
        smooth: true,
        lineStyle: { width: 3, color: '#2563eb' },
        itemStyle: { color: '#2563eb' }
      },
      {
        name: 'Variance Band (±1σ)',
        type: 'line',
        data: upper,
        lineStyle: { opacity: 0 },
        stack: 'confidence-band',
        symbol: 'none'
      },
      {
        name: 'Variance Band (±1σ)',
        type: 'line',
        data: upper.map((u, i) => u - lower[i]),
        lineStyle: { opacity: 0 },
        areaStyle: { color: 'rgba(37, 99, 235, 0.12)' },
        stack: 'confidence-band',
        symbol: 'none'
      }
    ]
  };

  return <ReactECharts option={options} style={{ height, width: '100%' }} notMerge={true} lazyUpdate={true} />;
};
