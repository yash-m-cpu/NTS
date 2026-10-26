import React, { useState } from 'react';
import { CheckCircle2 } from 'lucide-react';
import { DataTable, type Column } from '../components/common/DataTable';

interface ComparisonRow {
  metric: string;
  periodA: number;
  periodB: number;
  delta: string;
  relative: string;
  pValue: number;
  significance: string;
}

export const View08HistoricalComparison: React.FC = () => {
  const [periodA, setPeriodA] = useState('Sprint 42 (Pre-Remodel Layout)');
  const [periodB, setPeriodB] = useState('Sprint 44 (Acoustic Baffle Pods)');

  const comparisonData: ComparisonRow[] = [
    {
      metric: 'Workflow Efficiency Score (Scorecard A)',
      periodA: 68.2,
      periodB: 77.4,
      delta: '+9.2 pts',
      relative: '+13.5%',
      pValue: 0.004,
      significance: 'Significant (p < 0.01)'
    },
    {
      metric: 'Focus Interruption Frequency (events/hr)',
      periodA: 2.8,
      periodB: 1.1,
      delta: '-1.7 / hr',
      relative: '-60.7%',
      pValue: 0.001,
      significance: 'Significant (p < 0.01)'
    },
    {
      metric: 'Corridor Congestion Ratio (%)',
      periodA: 7.4,
      periodB: 1.2,
      delta: '-6.2%',
      relative: '-83.8%',
      pValue: 0.002,
      significance: 'Significant (p < 0.01)'
    },
    {
      metric: 'Workstation Occupancy Rate (%)',
      periodA: 79.1,
      periodB: 74.8,
      delta: '-4.3%',
      relative: '-5.4%',
      pValue: 0.142,
      significance: 'Not Significant (p ≥ 0.05)'
    },
    {
      metric: 'Active Collaboration Ratio (%)',
      periodA: 16.5,
      periodB: 24.2,
      delta: '+7.7%',
      relative: '+46.7%',
      pValue: 0.008,
      significance: 'Significant (p < 0.01)'
    }
  ];

  const columns: Column<ComparisonRow>[] = [
    { header: 'Metric Name', accessorKey: 'metric', className: 'font-semibold text-gray-900' },
    { header: 'Period A (Baseline)', accessorKey: 'periodA', className: 'font-mono' },
    { header: 'Period B (Test)', accessorKey: 'periodB', className: 'font-mono text-blue-600' },
    { header: 'Absolute Delta', accessorKey: 'delta', className: 'font-mono font-medium' },
    { header: 'Relative Change', accessorKey: 'relative', className: 'font-mono font-medium' },
    { header: 'p-Value', accessorKey: 'pValue', className: 'font-mono text-gray-500' },
    {
      header: 'Statistical Significance',
      cell: (row) => (
        <span
          className={`px-2 py-0.5 rounded text-[11px] font-semibold border ${
            row.significance.includes('Significant (p <')
              ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
              : 'bg-gray-100 text-gray-500 border-gray-200'
          }`}
        >
          {row.significance}
        </span>
      )
    }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
          <span>⚖️ View 08: Historical Trend Comparison (A/B Testing Engine)</span>
        </h2>
        <p className="text-xs text-gray-500 mt-1">
          Scientifically measure the operational impact of architectural layout changes, desk reorganization, or hybrid work policy adjustments using two-sample statistical testing.
        </p>
      </div>

      {/* Window Selectors */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-2 shadow-xs">
          <label className="text-xs font-semibold uppercase tracking-wider text-gray-600 block">
            Baseline Window (Period A)
          </label>
          <select
            value={periodA}
            onChange={(e) => setPeriodA(e.target.value)}
            className="w-full bg-gray-50 border border-gray-300 text-gray-800 text-xs rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500 cursor-pointer"
          >
            <option>Sprint 42 (Pre-Remodel Layout)</option>
            <option>Q1 Baseline (Open Bench Seating)</option>
            <option>October 1-7, 2026</option>
          </select>
        </div>

        <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-2 shadow-xs">
          <label className="text-xs font-semibold uppercase tracking-wider text-gray-600 block">
            Experimental Window (Period B)
          </label>
          <select
            value={periodB}
            onChange={(e) => setPeriodB(e.target.value)}
            className="w-full bg-gray-50 border border-gray-300 text-gray-800 text-xs rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500 cursor-pointer"
          >
            <option>Sprint 44 (Acoustic Baffle Pods)</option>
            <option>Q2 Layout (Dedicated Focus Zone)</option>
            <option>October 8-14, 2026</option>
          </select>
        </div>
      </div>

      {/* Comparative Metric Delta Table */}
      <div className="space-y-3">
        <h4 className="text-sm font-semibold text-gray-900">📊 Comparative Metric Deltas & Hypothesis Validation</h4>
        <DataTable columns={columns} data={comparisonData} />
      </div>

      {/* Statistical Summary Callout */}
      <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-900 space-y-2 shadow-xs">
        <h5 className="font-semibold text-emerald-800 flex items-center gap-2 text-sm">
          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          <span>A/B Intervention Outcome: Statistically Verified Success</span>
        </h5>
        <ul className="list-disc pl-5 space-y-1 text-gray-700">
          <li>
            Acoustic separation pods achieved a <b>60.7% reduction</b> in focus interruptions (<i>p = 0.001</i>).
          </li>
          <li>
            Circulation lane widening eliminated congestion bottlenecks with an <b>83.8% drop</b> (<i>p = 0.002</i>).
          </li>
          <li>
            Workstation occupancy shift was statistically neutral (<i>p = 0.142</i>), confirming productivity gains did not require increased desk confinement.
          </li>
        </ul>
      </div>
    </div>
  );
};
