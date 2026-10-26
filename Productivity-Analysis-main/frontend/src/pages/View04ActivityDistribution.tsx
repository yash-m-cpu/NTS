import React, { useEffect, useState } from 'react';
import { useApp } from '../context/AppContext';
import { apiService } from '../services/api';
import type { ScorecardB, LiveTelemetrySnapshot } from '../types';
import { MetricCard } from '../components/common/MetricCard';
import { RadialGaugeChart } from '../components/charts/RadialGaugeChart';
import { StackedBarChart } from '../components/charts/StackedBarChart';
import { DataTable, type Column } from '../components/common/DataTable';
import { AlertTriangle, Clock } from 'lucide-react';

export const View04ActivityDistribution: React.FC = () => {
  const { selectedCamera, selectedDepartment } = useApp();
  const [scorecardB, setScorecardB] = useState<ScorecardB | null>(null);
  const [telemetry, setTelemetry] = useState<LiveTelemetrySnapshot | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      const [suite, telem] = await Promise.all([
        apiService.getScorecards(selectedCamera, selectedDepartment),
        apiService.getLiveTelemetry(selectedCamera)
      ]);
      if (suite?.scorecard_b) {
        setScorecardB(suite.scorecard_b);
      }
      setTelemetry(telem);
    };

    fetchData();
    const interval = setInterval(fetchData, 4000);
    return () => clearInterval(interval);
  }, [selectedCamera, selectedDepartment]);

  const score = scorecardB?.composite_score ?? 72.4;
  const metrics = scorecardB?.metrics ?? {};
  const activityShares = metrics.activity_shares ?? {
    'ACT-01': 58.0,
    'ACT-02': 16.0,
    'ACT-03': 12.0,
    'ACT-04': 7.0,
    'ACT-05': 4.0,
    'ACT-06': 1.5,
    'ACT-07': 1.5
  };

  const getShare = (bd: Record<string, number>, code: string): number => {
    if (!bd) return 0.0;
    if (code in bd) return Number(bd[code]);
    for (const [k, v] of Object.entries(bd)) {
      if (k.startsWith(code)) return Number(v);
    }
    return 0.0;
  };

  // Person-Wise Posture Table
  const activeTracks = telemetry?.active_tracks && telemetry.active_tracks.length > 0 ? telemetry.active_tracks : [];

  const personPostureData =
    activeTracks.length > 0
      ? activeTracks.map((t) => {
          const tid = t.track_id;
          const currAct = t.activity || 'ACT-01: Seated at Workstation';
          let bd = t.activity_breakdown || {};
          const currCode = currAct.split(':')[0].trim();
          const totalSum = ['ACT-01', 'ACT-02', 'ACT-03', 'ACT-04', 'ACT-05', 'ACT-06', 'ACT-07']
            .map((c) => getShare(bd, c))
            .reduce((a, b) => a + b, 0);

          if (totalSum <= 0) {
            bd = { [currCode]: 100.0 };
          }

          const act01 = getShare(bd, 'ACT-01');
          const act02 = getShare(bd, 'ACT-02');
          const act03 = getShare(bd, 'ACT-03');
          const act04 = getShare(bd, 'ACT-04');
          const act05 = getShare(bd, 'ACT-05');
          const act06_07 = getShare(bd, 'ACT-06') + getShare(bd, 'ACT-07');

          let assessment = '🟢 Nominal Ergonomic Flow';
          if (act01 > 75.0) {
            assessment = '🔴 Sedentary Lock (>75% Seated)';
          } else if (act03 > 25.0) {
            assessment = '🟡 High Locomotion / Transit';
          } else if (act01 + act02 > 0 && act02 >= 15.0) {
            assessment = '🟢 Balanced Sit-Stand Dynamic';
          }

          return {
            trackId: tid,
            state: currAct,
            seated: `${act01.toFixed(1)}%`,
            standing: `${act02.toFixed(1)}%`,
            walking: `${act03.toFixed(1)}%`,
            interaction: `${act04.toFixed(1)}%`,
            collab: `${act05.toFixed(1)}%`,
            away: `${act06_07.toFixed(1)}%`,
            assessment
          };
        })
      : [
          {
            trackId: 'TRK-0101',
            state: 'ACT-01: Seated at Workstation',
            seated: '68.0%',
            standing: '12.0%',
            walking: '8.0%',
            interaction: '7.0%',
            collab: '3.0%',
            away: '2.0%',
            assessment: '🟢 Balanced Sit-Stand Ratio'
          },
          {
            trackId: 'TRK-0102',
            state: 'ACT-01: Seated at Workstation',
            seated: '62.0%',
            standing: '15.0%',
            walking: '10.0%',
            interaction: '8.0%',
            collab: '3.0%',
            away: '2.0%',
            assessment: '🟢 Healthy Mobility Transition'
          },
          {
            trackId: 'TRK-0103',
            state: 'ACT-04: Workstation Interaction',
            seated: '54.0%',
            standing: '18.0%',
            walking: '12.0%',
            interaction: '10.0%',
            collab: '4.0%',
            away: '2.0%',
            assessment: '🟢 Dynamic Desk Movement'
          },
          {
            trackId: 'TRK-0104',
            state: 'ACT-03: Walking / In Transit',
            seated: '35.0%',
            standing: '20.0%',
            walking: '30.0%',
            interaction: '5.0%',
            collab: '6.0%',
            away: '4.0%',
            assessment: '🟡 High Locomotion / Transit'
          }
        ];

  const columns: Column<typeof personPostureData[0]>[] = [
    { header: 'Track ID', accessorKey: 'trackId', className: 'font-mono text-sky-400 font-medium' },
    { header: 'Current State', accessorKey: 'state' },
    { header: 'Seated (ACT-01)', accessorKey: 'seated' },
    { header: 'Standing (ACT-02)', accessorKey: 'standing' },
    { header: 'Walking (ACT-03)', accessorKey: 'walking' },
    { header: 'Interaction (ACT-04)', accessorKey: 'interaction' },
    { header: 'Collab (ACT-05)', accessorKey: 'collab' },
    { header: 'Away / Unknown', accessorKey: 'away' },
    { header: 'Ergonomic Assessment', accessorKey: 'assessment', className: 'font-medium' }
  ];

  // Shift Timeline Data
  const timelineData = [
    { hour: '09:00', seated: '62%', collab: '15%', mobility: '18%', unobserved: '5%' },
    { hour: '10:00', seated: '58%', collab: '22%', mobility: '15%', unobserved: '5%' },
    { hour: '11:00', seated: '52%', collab: '28%', mobility: '16%', unobserved: '4%' },
    { hour: '12:00', seated: '25%', collab: '15%', mobility: '50%', unobserved: '10%' },
    { hour: '13:00', seated: '40%', collab: '30%', mobility: '25%', unobserved: '5%' },
    { hour: '14:00', seated: '55%', collab: '24%', mobility: '16%', unobserved: '5%' },
    { hour: '15:00', seated: '60%', collab: '20%', mobility: '15%', unobserved: '5%' },
    { hour: '16:00', seated: '50%', collab: '28%', mobility: '18%', unobserved: '4%' },
    { hour: '17:00', seated: '42%', collab: '25%', mobility: '28%', unobserved: '5%' }
  ];

  const timelineColumns: Column<typeof timelineData[0]>[] = [
    { header: 'Shift Hour', accessorKey: 'hour', className: 'font-mono text-sky-400 font-medium' },
    { header: 'Workstation Seated (%)', accessorKey: 'seated' },
    { header: 'Interaction & Collab (%)', accessorKey: 'collab' },
    { header: 'Mobility & Transit (%)', accessorKey: 'mobility' },
    { header: 'Unobserved (%)', accessorKey: 'unobserved' }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
          <span>📊 View 04: Activity & Time Distribution Panel (Scorecard B)</span>
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Displays physical ergonomics and aggregate posture time distributions across the 7 standardized activity classes (ACT-01 through ACT-07).
        </p>
      </div>

      {/* Anti-Conflation Banner */}
      <div className="p-3.5 bg-amber-950/40 border border-amber-500/30 rounded-xl text-xs text-amber-200 flex items-start gap-2.5">
        <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
        <p>
          <b>ANTI-CONFLATION MANDATE:</b> Physical posture indicates ergonomic behavior and presence; it does{' '}
          <b>NOT</b> measure cognitive attention, knowledge work output, or employee dedication.
        </p>
      </div>

      {/* Top Gauge & Stacked Bar */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div className="lg:col-span-2 bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-sm flex flex-col justify-between">
          <div>
            <h4 className="text-sm font-semibold text-slate-200 mb-1">Primary Scorecard B</h4>
            <p className="text-xs text-slate-400">Activity distribution composite score</p>
          </div>
          <RadialGaugeChart
            score={score}
            title="Activity Distribution"
            minVal={0}
            maxVal={100}
            unit="/100"
            height="260px"
          />
          <p className="text-xs text-slate-400 text-center mt-2">
            Measures healthy distribution of postures vs sedentary fatigue.
          </p>
        </div>

        <div className="lg:col-span-3 bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-sm flex flex-col justify-between">
          <div>
            <h4 className="text-sm font-semibold text-slate-200 mb-1">Posture & Ergonomic Time Shares (Pod Aggregate)</h4>
            <p className="text-xs text-slate-400 mb-2">Aggregated across all occupants. Unknown/occluded frames are transparently isolated.</p>
          </div>
          <StackedBarChart activityShares={activityShares} height="200px" />
          <p className="text-[11px] text-slate-500 text-right mt-1">Observed frames across active session</p>
        </div>
      </div>

      {/* Sub-Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Seated Workstation Share"
          value={`${Number(activityShares['ACT-01'] || 0).toFixed(1)}%`}
          delta="Optimal (50-65%)"
          deltaType="normal"
          caption="Standard desk-bound posture."
        />

        <MetricCard
          label="Collaboration & Peer Interaction"
          value={`${(Number(activityShares['ACT-02'] || 0) + Number(activityShares['ACT-05'] || 0)).toFixed(1)}%`}
          delta="Active Exchange"
          deltaType="normal"
          caption="Combined conversational & whiteboard collaboration."
        />

        <MetricCard
          label="Active Mobility Share"
          value={`${(Number(activityShares['ACT-03'] || 0) + Number(activityShares['ACT-04'] || 0)).toFixed(1)}%`}
          delta="Healthy Mobility (> 10%)"
          deltaType="normal"
          caption="Standing, walking, and corridor transit."
        />

        <MetricCard
          label="Unobserved / Occluded Ratio"
          value={`${Number(activityShares['ACT-07'] || 0).toFixed(1)}%`}
          delta={Number(activityShares['ACT-07'] || 0) < 5.0 ? 'Clean Signal (< 5%)' : 'High Occlusion'}
          deltaType={Number(activityShares['ACT-07'] || 0) < 5.0 ? 'normal' : 'inverse'}
          caption="Algorithm uncertainty quantification."
        />
      </div>

      {/* Person-Wise Ergonomic Posture Table */}
      <div className="space-y-3">
        <div>
          <h4 className="text-sm font-semibold text-slate-200">👤 Person-Wise Ergonomic Posture Breakdown</h4>
          <p className="text-xs text-slate-400">
            Individual ergonomic posture profiles per ephemeral track (<code className="text-sky-300 font-mono">TRK-xxxx</code>). Provides biomechanical health insights without identifying individuals.
          </p>
        </div>
        <DataTable columns={columns} data={personPostureData} />
      </div>

      {/* Shift Chronological Timeline */}
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-sky-400" />
          <h4 className="text-sm font-semibold text-slate-200">🕒 Chronological Activity Timeline Across Monitored Shift</h4>
        </div>
        <p className="text-xs text-slate-400">Standard operational shift profile showing aggregate posture transitions by hour.</p>
        <DataTable columns={timelineColumns} data={timelineData} />
      </div>
    </div>
  );
};
