import React from 'react';
import ReactECharts from 'echarts-for-react';

interface PsiGaugeChartProps {
  psiScore?: number;
  height?: string;
}

export const PsiGaugeChart: React.FC<PsiGaugeChartProps> = ({
  psiScore = 0.048,
  height = '240px'
}) => {
  // PSI < 0.10: Stable, 0.10 <= PSI < 0.25: Moderate Drift, PSI >= 0.25: Significant Drift
  const colorStops: [number, string][] = [
    [0.4, '#10b981'], // Emerald: Stable (< 0.10)
    [0.7, '#f59e0b'], // Amber: Moderate drift (0.10 - 0.25)
    [1.0, '#ef4444']  // Red: High drift (> 0.25)
  ];

  const options = {
    backgroundColor: 'transparent',
    title: {
      text: 'Population Stability Index (PSI)',
      left: 'center',
      textStyle: { fontSize: 13, color: '#1e293b', fontWeight: 600 }
    },
    series: [
      {
        type: 'gauge',
        min: 0.0,
        max: 0.35,
        splitNumber: 7,
        axisLine: { lineStyle: { width: 12, color: colorStops } },
        axisTick: { show: false },
        splitLine: { length: 8, lineStyle: { width: 2, color: '#cbd5e1' } },
        axisLabel: { distance: 16, fontSize: 9, color: '#64748b' },
        pointer: { width: 5, itemStyle: { color: '#2563eb' } },
        detail: {
          valueAnimation: true,
          fontSize: 20,
          fontWeight: 'bold',
          offsetCenter: [0, '50%'],
          formatter: '{value}',
          color: '#0f172a'
        },
        data: [{ value: Number(psiScore.toFixed(3)), name: 'PSI Drift' }]
      }
    ]
  };

  return <ReactECharts option={options} style={{ height, width: '100%' }} notMerge={true} lazyUpdate={true} />;
};
