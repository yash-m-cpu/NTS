import React from 'react';
import ReactECharts from 'echarts-for-react';

interface StackedBarChartProps {
  activityShares: Record<string, number>;
  height?: string;
}

export const StackedBarChart: React.FC<StackedBarChartProps> = ({
  activityShares,
  height = '180px'
}) => {
  const labels: Record<string, string> = {
    'ACT-01': 'Workstation Seated',
    'ACT-02': 'Active Interaction',
    'ACT-03': 'Standing / Walking',
    'ACT-04': 'Corridor Transit',
    'ACT-05': 'Whiteboard / Collab',
    'ACT-06': 'Personal Screen',
    'ACT-07': 'Unobserved / Occluded'
  };

  const colors: Record<string, string> = {
    'ACT-01': '#2b82c9', // Steel Blue
    'ACT-02': '#2ecc71', // Emerald Green
    'ACT-03': '#f39c12', // Warm Orange
    'ACT-04': '#9b59b6', // Purple
    'ACT-05': '#1abc9c', // Turquoise
    'ACT-06': '#e74c3c', // Crimson
    'ACT-07': '#95a5a6'  // Muted Gray
  };

  const series = Object.entries(labels).map(([code, name]) => {
    let val = 0.0;
    if (code in activityShares) {
      val = Number(activityShares[code]);
    } else {
      for (const [k, v] of Object.entries(activityShares)) {
        if (k.startsWith(code)) {
          val = Number(v);
          break;
        }
      }
    }

    return {
      name: `${code}: ${name}`,
      type: 'bar',
      stack: 'total',
      emphasis: { focus: 'series' },
      itemStyle: { color: colors[code] || '#888' },
      data: [Number(val.toFixed(1))]
    };
  });

  const options = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: any) => {
        if (!Array.isArray(params)) return '';
        const lines = params.map((p: any) => `${p.seriesName}: <b>${p.value}%</b>`);
        return `${params[0]?.name || ''}<br/>${lines.join('<br/>')}`;
      }
    },
    legend: {
      top: '0%',
      textStyle: { fontSize: 11, color: '#94a3b8' }
    },
    grid: { left: '3%', right: '4%', bottom: '10%', top: '35%', containLabel: true },
    xAxis: {
      type: 'value',
      max: 100,
      axisLabel: { formatter: '{value}%', color: '#94a3b8' },
      splitLine: { lineStyle: { color: '#1e293b' } }
    },
    yAxis: {
      type: 'category',
      data: ['Observed Time Share'],
      axisLabel: { color: '#94a3b8' }
    },
    series
  };

  return <ReactECharts option={options} style={{ height, width: '100%' }} notMerge={true} lazyUpdate={true} />;
};
