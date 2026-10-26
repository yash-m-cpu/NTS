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
    [0.4, '#f56c6c'], // Red
    [0.7, '#e6a23c'], // Amber
    [1.0, '#67c23a']  // Green
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
          width: 6,
          length: '60%',
          itemStyle: { color: '#3b82f6' }
        },
        axisTick: { show: false },
        splitLine: { length: 8, lineStyle: { width: 2, color: '#666' } },
        axisLabel: { distance: 18, color: '#cbd5e1', fontSize: 11 },
        anchor: {
          show: true,
          showAbove: true,
          size: 16,
          itemStyle: { borderWidth: 4, borderColor: '#3b82f6', color: '#ffffff' }
        },
        title: {
          show: true,
          offsetCenter: [0, '72%'],
          fontSize: 13,
          fontWeight: 500,
          color: '#e2e8f0'
        },
        detail: {
          valueAnimation: true,
          fontSize: 26,
          fontWeight: 'bold',
          offsetCenter: [0, '35%'],
          formatter: `{value}${unit}`,
          color: '#f8fafc'
        },
        data: [{ value: Number(score.toFixed(1)), name: title }]
      }
    ]
  };

  return <ReactECharts option={options} style={{ height, width: '100%' }} notMerge={true} lazyUpdate={true} />;
};
