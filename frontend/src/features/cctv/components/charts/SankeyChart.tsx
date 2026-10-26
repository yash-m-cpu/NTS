import React from 'react';
import ReactECharts from 'echarts-for-react';

interface SankeyChartProps {
  height?: string;
}

export const SankeyChart: React.FC<SankeyChartProps> = ({ height = '340px' }) => {
  const nodes = [
    { name: 'Desk Pod A' },
    { name: 'Desk Pod B' },
    { name: 'Meeting Room 1' },
    { name: 'Collaboration Bar' },
    { name: 'Corridor Spine' },
    { name: 'Break Area / Kitchen' }
  ];

  const links = [
    { source: 'Desk Pod A', target: 'Corridor Spine', value: 35 },
    { source: 'Desk Pod B', target: 'Corridor Spine', value: 28 },
    { source: 'Corridor Spine', target: 'Meeting Room 1', value: 22 },
    { source: 'Corridor Spine', target: 'Collaboration Bar', value: 18 },
    { source: 'Corridor Spine', target: 'Break Area / Kitchen', value: 23 },
    { source: 'Meeting Room 1', target: 'Desk Pod A', value: 12 },
    { source: 'Meeting Room 1', target: 'Desk Pod B', value: 10 },
    { source: 'Collaboration Bar', target: 'Desk Pod A', value: 10 },
    { source: 'Break Area / Kitchen', target: 'Desk Pod B', value: 15 }
  ];

  const options = {
    backgroundColor: 'transparent',
    title: {
      text: 'Zone Transition Circulation Flows',
      left: 'center',
      textStyle: { fontSize: 14, color: '#1e293b', fontWeight: 600 }
    },
    tooltip: { trigger: 'item', triggerOn: 'mousemove' },
    series: [
      {
        type: 'sankey',
        layout: 'none',
        emphasis: { focus: 'adjacency' },
        data: nodes,
        links: links,
        label: { color: '#334155', fontSize: 11, fontWeight: 500 },
        lineStyle: { color: 'gradient', curveness: 0.5, opacity: 0.5 }
      }
    ]
  };

  return <ReactECharts option={options} style={{ height, width: '100%' }} notMerge={true} lazyUpdate={true} />;
};
