import React from 'react';
import ReactECharts from 'echarts-for-react';

interface RadialGaugeChartProps {
  score: number;
  title?: string;
  minVal?: number;
  maxVal?: number;
  unit?: string;
  height?: string;
}

export const RadialGaugeChart: React.FC<RadialGaugeChartProps> = ({
  score,
  title = 'Score',
  minVal = 0,
  maxVal = 100,
  unit = '%',
  height = '260px'
}) => {
  const colorStops: [number, string][] = [
    [0.4, '#ef4444'], // Red
    [0.7, '#f59e0b'], // Amber
    [1.0, '#10b981']  // Green
  ];

  const options = {
    backgroundColor: 'transparent',
    tooltip: {
      formatter: `{a} <br/>{b} : {c}${unit}`
    },
    series: [
      {
        name: title,
        type: 'gauge',
        min: minVal,
        max: maxVal,
        progress: { show: true, width: 14 },
        axisLine: {
          lineStyle: {
            width: 14,
            color: colorStops
          }
        },
        pointer: {
          show: true,
          width: 5,
          length: '60%',
          itemStyle: { color: '#2563eb' }
        },
        axisTick: { show: false },
        splitLine: { length: 8, lineStyle: { width: 2, color: '#cbd5e1' } },
        axisLabel: { distance: 18, color: '#64748b', fontSize: 11 },
        anchor: {
          show: true,
          showAbove: true,
          size: 14,
          itemStyle: { borderWidth: 3, borderColor: '#2563eb', color: '#ffffff' }
        },
        title: {
          show: true,
          offsetCenter: [0, '72%'],
          fontSize: 13,
          fontWeight: 600,
          color: '#334155'
        },
        detail: {
          valueAnimation: true,
          fontSize: 26,
          fontWeight: 'bold',
          offsetCenter: [0, '35%'],
          formatter: `{value}${unit}`,
          color: '#0f172a'
        },
        data: [{ value: Number(score.toFixed(1)), name: title }]
      }
    ]
  };

  return <ReactECharts option={options} style={{ height, width: '100%' }} notMerge={true} lazyUpdate={true} />;
};
