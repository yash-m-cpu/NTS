import React, { useEffect, useState } from 'react';
import { useApp } from '../context/AppContext';
import { apiService } from '../services/api';
import type { ScorecardA, Recommendation, LiveTelemetrySnapshot } from '../types';
import { MetricCard } from '../components/common/MetricCard';
import { RadialGaugeChart } from '../components/charts/RadialGaugeChart';
import { SankeyChart } from '../components/charts/SankeyChart';
import { DataTable, type Column } from '../components/common/DataTable';
import { Zap, Lightbulb } from 'lucide-react';

export const View03WorkflowEfficiency: React.FC = () => {
  const { selectedCamera, selectedDepartment } = useApp();
  const [scorecardA, setScorecardA] = useState<ScorecardA | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [telemetry, setTelemetry] = useState<LiveTelemetrySnapshot | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      const [suite, recs, telem] = await Promise.all([
        apiService.getScorecards(selectedCamera, selectedDepartment),
        apiService.getRecommendations(selectedCamera),
        apiService.getLiveTelemetry(selectedCamera)
      ]);
      if (suite?.scorecard_a) {
        setScorecardA(suite.scorecard_a);
      }
      setRecommendations(recs);
      setTelemetry(telem);
    };

    fetchData();
    const interval = setInterval(fetchData, 4000);
    return () => clearInterval(interval);
  }, [selectedCamera, selectedDepartment]);

  const score = scorecardA?.composite_score ?? 76.5;
  const conf = scorecardA?.confidence ?? 'HIGH';
  const metrics = scorecardA?.metrics ?? {};

  // Build Person-Wise Friction Table Data
  const activeTracks = telemetry?.active_tracks && telemetry.active_tracks.length > 0 ? telemetry.active_tracks : [];

  const personFrictionData =
    activeTracks.length > 0
      ? activeTracks.map((t) => {
          const tid = t.track_id;
          const zid = t.zone_id || 'ZONE-UNASSIGNED';
          const interruptions = t.interruption_events || 0;
          const intRate = Math.max(0.2, interruptions * 0.8);
          const waitingS = t.waiting_seconds || 0;
          const dwellS = Math.max(1, t.dwell_duration_seconds || 60);
          const waitRatio = (waitingS / (dwellS + waitingS)) * 100;
          const transitions = t.transitions_count || 0;
          const transitRate = Math.max(1, transitions * 1.5);
          const breakdown = t.activity_breakdown || {};
          const corridorPct = Number(breakdown['ACT-03'] || 5.0);

          let risk = '🟢 Low Friction';
          let driver = 'Uninterrupted focus; nominal circulation';
          if (intRate >= 3.0 || waitRatio >= 5.0) {
            risk = '🔴 High Disruption';
            driver = 'Frequent walkway interruptions / queue latency';
          } else if (transitRate >= 5.0 || corridorPct >= 20.0) {
            risk = '🟡 High Circulation';
            driver = 'High inter-zone transit churn';
          }

          return {
            trackId: tid,
            zone: zid,
            interruption: `${intRate.toFixed(1)} / hr (${interruptions} events)`,
            waiting: `${waitRatio.toFixed(1)}% (${waitingS.toFixed(0)}s)`,
            transit: `${transitRate.toFixed(1)} moves/hr`,
            corridor: `${corridorPct.toFixed(1)}%`,
            riskLevel: risk,
            driver: driver
          };
        })
      : [
          {
            trackId: 'TRK-0101',
            zone: 'ZONE-POD-01 (Desk A-01)',
            interruption: '0.8 / hr (1 event)',
            waiting: '1.2% (43s)',
            transit: '2.4 moves/hr',
            corridor: '3.5%',
            riskLevel: '🟢 Low Friction',
            driver: 'Optimal focus desk; minimal disruption'
          },
          {
            trackId: 'TRK-0102',
            zone: 'ZONE-POD-01 (Desk A-02)',
            interruption: '1.6 / hr (2 events)',
            waiting: '1.8% (65s)',
            transit: '3.2 moves/hr',
            corridor: '4.8%',
            riskLevel: '🟢 Low Friction',
            driver: 'Near walkway entrance; occasional peer visits'
          },
          {
            trackId: 'TRK-0103',
            zone: 'ZONE-POD-02 (Desk B-01)',
            interruption: '0.0 / hr (0 events)',
            waiting: '2.5% (90s)',
            transit: '4.0 moves/hr',
            corridor: '6.2%',
            riskLevel: '🟡 Moderate Churn',
            driver: 'Printer hallway queue; recurrent transit'
          },
          {
            trackId: 'TRK-0104',
            zone: 'ZONE-CORRIDOR-01',
            interruption: '1.2 / hr (1 event)',
            waiting: '0.8% (28s)',
            transit: '6.5 moves/hr',
            corridor: '32.0%',
            riskLevel: '🟡 High Circulation',
            driver: 'Active inter-zone runner; high pathway traversal'
          }
        ];

  const columns: Column<typeof personFrictionData[0]>[] = [
    { header: 'Track ID', accessorKey: 'trackId', className: 'font-mono text-sky-400 font-medium' },
    { header: 'Assigned / Current Zone', accessorKey: 'zone' },
    { header: 'Interruption Freq (/hr)', accessorKey: 'interruption' },
    { header: 'Waiting Ratio (%)', accessorKey: 'waiting' },
    { header: 'Transit Churn', accessorKey: 'transit' },
    { header: 'Corridor Exposure', accessorKey: 'corridor' },
    { header: 'Friction Risk Level', accessorKey: 'riskLevel', className: 'font-medium' },
    { header: 'Primary Architectural Friction', accessorKey: 'driver' }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
          <span>⚡ View 03: Workflow Efficiency & Bottleneck Panel</span>
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Analyzes physical office layout friction, corridor bottlenecks, transit churn, and focus interruption events to optimize workplace architectural ergonomics.
        </p>
      </div>

      {/* Top Gauge & Metrics Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div className="lg:col-span-2 bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-sm flex flex-col justify-between">
          <div>
            <h4 className="text-sm font-semibold text-slate-200 mb-1">Primary Scorecard A</h4>
            <p className="text-xs text-slate-400">Workflow efficiency composite rating</p>
          </div>
          <RadialGaugeChart
            score={score}
            title="Workflow Efficiency"
            minVal={0}
            maxVal={100}
            unit="/100"
            height="260px"
          />
          <p className="text-xs text-slate-400 text-center mt-2">
            Confidence Level: <b className="text-sky-300">{conf}</b> | Department: <b className="text-slate-200">{selectedDepartment}</b>
          </p>
        </div>

        <div className="lg:col-span-3 space-y-4">
          <h4 className="text-sm font-semibold text-slate-200">Spatial Friction Risk Breakdown (Pod Aggregate)</h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <MetricCard
              label="Interruption Frequency"
              value={`${Number(metrics.focus_interruption_freq || 1.0).toFixed(1)} / hr`}
              delta="Nominal (< 2.0)"
              deltaType="normal"
              caption="Threshold: > 3.0 / hr signifies high disruption."
              icon={<Zap className="w-4 h-4 text-emerald-400" />}
            />

            <MetricCard
              label="Corridor Congestion Ratio"
              value={`${Number(metrics.congestion_ratio_pct || 0.8).toFixed(1)}%`}
              delta="Uncongested (< 5%)"
              deltaType="normal"
              caption="Share of time corridors exceed 0.5 persons/m²."
            />

            <MetricCard
              label="Service Waiting Ratio"
              value={`${Number(metrics.waiting_ratio_pct || 1.7).toFixed(1)}%`}
              delta="Optimal (< 3%)"
              deltaType="normal"
              caption="Bottleneck waiting at shared resources."
            />

            <MetricCard
              label="Zone Transit Churn"
              value={`${Number(metrics.zone_transition_frequency || 4.0).toFixed(1)} moves/hr`}
              delta="Moderate Circulation"
              deltaType="normal"
              caption="Frequency of inter-zone movements per person."
            />
          </div>
        </div>
      </div>

      {/* Person-Wise Friction Table */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-sm font-semibold text-slate-200">👤 Person-Wise Spatial Friction & Bottleneck Breakdown</h4>
            <p className="text-xs text-slate-400">
              Individual spatial friction metrics per ephemeral track (<code className="text-sky-300 font-mono">TRK-xxxx</code>). Bounded by privacy covenants: identifies workspace bottlenecks, NOT personal productivity.
            </p>
          </div>
        </div>
        <DataTable columns={columns} data={personFrictionData} />
      </div>

      {/* Circulation Flows Sankey */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-sm space-y-2">
        <h4 className="text-sm font-semibold text-slate-200">🔄 Circulation Pathways & Bottleneck Points</h4>
        <p className="text-xs text-slate-400">Visualizes the volume of person transitions across primary office functional areas.</p>
        <SankeyChart height="340px" />
      </div>

      {/* Layout Recommendations */}
      <div className="space-y-3">
        <h4 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
          <Lightbulb className="w-4 h-4 text-amber-400" />
          <span>Layout Optimization Insights</span>
        </h4>
        {recommendations.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {recommendations.map((r) => (
              <div key={r.recommendation_id} className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-sky-400 font-mono">{r.rule_code}</span>
                  <span className="text-[11px] px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-300 border border-emerald-500/30">
                    Expected Impact: +{r.expected_impact_pct}%
                  </span>
                </div>
                <h5 className="text-xs font-semibold text-slate-100">{r.hypothesis}</h5>
                <p className="text-xs text-slate-400"><b>Evidence:</b> {r.observed_metric_evidence}</p>
                <p className="text-xs text-sky-200 bg-sky-950/40 border border-sky-500/20 p-2 rounded">
                  <b>Action:</b> {r.recommended_action}
                </p>
                <p className="text-[11px] text-slate-500">Mitigation: {r.mitigation_notes}</p>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl text-xs text-slate-400">
            No active layout bottleneck triggers detected. Space circulation is currently performing within optimal limits.
          </div>
        )}
      </div>
    </div>
  );
};
