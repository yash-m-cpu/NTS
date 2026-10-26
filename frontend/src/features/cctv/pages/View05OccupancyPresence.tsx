import React, { useEffect, useState } from 'react';
import { useApp } from '../context/AppContext';
import { apiService } from '../../../services/cctvApi';
import type { ScorecardC, SpatialZone, Recommendation, LiveTelemetrySnapshot } from '../types';
import { MetricCard } from '../components/common/MetricCard';
import { RadialGaugeChart } from '../components/charts/RadialGaugeChart';
import { BarChart } from '../components/charts/BarChart';
import { TrendVarianceChart } from '../components/charts/TrendVarianceChart';
import { DataTable, type Column } from '../components/common/DataTable';
import { Building2, Lightbulb, CheckCircle2 } from 'lucide-react';

export const View05OccupancyPresence: React.FC = () => {
  const { selectedCamera, selectedDepartment } = useApp();
  const [scorecardC, setScorecardC] = useState<ScorecardC | null>(null);
  const [zones, setZones] = useState<SpatialZone[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [telemetry, setTelemetry] = useState<LiveTelemetrySnapshot | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      const [suite, zList, recs, telem] = await Promise.all([
        apiService.getScorecards(selectedCamera, selectedDepartment),
        apiService.getZones(selectedCamera),
        apiService.getRecommendations(selectedCamera),
        apiService.getLiveTelemetry(selectedCamera)
      ]);
      if (suite?.scorecard_c) {
        setScorecardC(suite.scorecard_c);
      }
      setZones(zList);
      setRecommendations(recs);
      setTelemetry(telem);
    };

    fetchData();
    const interval = setInterval(fetchData, 4000);
    return () => clearInterval(interval);
  }, [selectedCamera, selectedDepartment]);

  const score = scorecardC?.composite_score ?? 78.2;
  const metrics = scorecardC?.metrics ?? {};
  const wor = Number(metrics.workstation_occupancy_rate_pct ?? 75.0);
  const away = Number(metrics.away_time_ratio_pct ?? 25.0);

  const getShare = (bd: Record<string, number>, code: string): number => {
    if (!bd) return 0.0;
    if (code in bd) return Number(bd[code]);
    for (const [k, v] of Object.entries(bd)) {
      if (k.startsWith(code)) return Number(v);
    }
    return 0.0;
  };

  // Person-Wise Presence Table
  const activeTracks = telemetry?.active_tracks && telemetry.active_tracks.length > 0 ? telemetry.active_tracks : [];

  const personPresenceData =
    activeTracks.length > 0
      ? activeTracks.map((t) => {
          const tid = t.track_id;
          const zid = t.zone_id || 'ZONE-UNASSIGNED';
          const dwellMins = (t.dwell_duration_seconds || 0) / 60.0;
          const transitions = t.transitions_count || 0;
          const breakdown = t.activity_breakdown || {};
          const act = t.activity || '';

          let presenceRatio = getShare(breakdown, 'ACT-01') + getShare(breakdown, 'ACT-02') + getShare(breakdown, 'ACT-04');
          if (presenceRatio <= 0.0 && (act.includes('ACT-01') || act.includes('ACT-02') || act.includes('ACT-04'))) {
            presenceRatio = 100.0;
          }

          let state = '⚪ UNVERIFIED';
          if (act.includes('ACT-01') || act.includes('ACT-04')) {
            state = '🟢 OCCUPIED (Active Seated)';
          } else if (act.includes('ACT-02')) {
            state = '🟢 OCCUPIED (Standing Desk)';
          } else if (act.includes('ACT-03')) {
            state = '🔵 IN TRANSIT (Corridor)';
          } else if (act.includes('ACT-06')) {
            state = '🟡 TRANSITORY_ABSENCE (Debounced)';
          }

          let planning = 'Flexible Hot-Desk Candidate';
          if (presenceRatio >= 75.0) {
            planning = 'Dedicated Workstation Required';
          } else if (presenceRatio >= 50.0) {
            planning = 'Standard Dedicated Allocation';
          }

          return {
            trackId: tid,
            zone: zid,
            presenceRatio: `${presenceRatio.toFixed(1)}%`,
            dwell: `${dwellMins.toFixed(1)} mins`,
            transitory: `${Math.max(1, Math.floor(transitions / 2))} events`,
            prolonged: `${Math.floor(transitions / 4)} events`,
            state,
            planning
          };
        })
      : [
          {
            trackId: 'TRK-0101',
            zone: 'ZONE-POD-01 (Desk A-01)',
            presenceRatio: '82.5%',
            dwell: '23.6 mins',
            transitory: '2 events',
            prolonged: '0 events',
            state: '🟢 OCCUPIED (Active Seated)',
            planning: 'Dedicated Workstation Required'
          },
          {
            trackId: 'TRK-0102',
            zone: 'ZONE-POD-01 (Desk A-02)',
            presenceRatio: '76.0%',
            dwell: '16.3 mins',
            transitory: '3 events',
            prolonged: '1 event',
            state: '🟢 OCCUPIED (Active Seated)',
            planning: 'Standard Dedicated Allocation'
          },
          {
            trackId: 'TRK-0103',
            zone: 'ZONE-POD-02 (Desk B-01)',
            presenceRatio: '64.0%',
            dwell: '10.7 mins',
            transitory: '4 events',
            prolonged: '1 event',
            state: '🟡 TRANSITORY_ABSENCE (Debounced)',
            planning: 'Flexible Hot-Desk Candidate'
          },
          {
            trackId: 'TRK-0104',
            zone: 'ZONE-CORRIDOR-01',
            presenceRatio: '35.0%',
            dwell: '2.5 mins',
            transitory: '5 events',
            prolonged: '2 events',
            state: '🔵 IN TRANSIT (Corridor)',
            planning: 'Agile / Touchdown Station Suitable'
          }
        ];

  const columns: Column<typeof personPresenceData[0]>[] = [
    { header: 'Track ID', accessorKey: 'trackId', className: 'font-mono text-blue-600 font-medium' },
    { header: 'Primary Workstation Zone', accessorKey: 'zone' },
    { header: 'Desk Presence Ratio (%)', accessorKey: 'presenceRatio' },
    { header: 'Continuous Dwell', accessorKey: 'dwell' },
    { header: 'Transitory Departures (<5m)', accessorKey: 'transitory' },
    { header: 'Prolonged Departures (>5m)', accessorKey: 'prolonged' },
    { header: 'Current Presence State', accessorKey: 'state', className: 'font-medium' },
    { header: 'Space Planning Affordance', accessorKey: 'planning' }
  ];

  const fallbackZones: SpatialZone[] = [
    { zone_id: 'DESK-A1', camera_id: selectedCamera, name: 'Desk A1', zone_type: 'WORKSTATION', capacity: 1, polygon_coords: [] },
    { zone_id: 'DESK-A2', camera_id: selectedCamera, name: 'Desk A2', zone_type: 'WORKSTATION', capacity: 1, polygon_coords: [] },
    { zone_id: 'DESK-B1', camera_id: selectedCamera, name: 'Desk B1', zone_type: 'WORKSTATION', capacity: 1, polygon_coords: [] },
    { zone_id: 'DESK-B2', camera_id: selectedCamera, name: 'Desk B2', zone_type: 'WORKSTATION', capacity: 1, polygon_coords: [] },
    { zone_id: 'COLLAB-1', camera_id: selectedCamera, name: 'Collab Pod', zone_type: 'COLLABORATION', capacity: 4, polygon_coords: [] },
    { zone_id: 'CORRIDOR-1', camera_id: selectedCamera, name: 'Corridor Spine', zone_type: 'CORRIDOR', capacity: 6, polygon_coords: [] }
  ];

  const shiftHours = ['08:00', '09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00'];
  const shiftRates = [22.0, 68.0, 84.0, 82.0, 41.0, 58.0, 86.0, 81.0, 74.0, 35.0];

  const rec01 = recommendations.find((r) => r.recommendation_id?.includes('REC-01') || r.rule_code?.includes('REC-01'));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
          <span>🏢 View 05: Workstation Occupancy & Spatial Presence (Scorecard C)</span>
        </h2>
        <p className="text-xs text-gray-500 mt-1">
          Provides objective spatial capacity data for facility managers and real estate planning.
          Differentiates momentary desk departures from persistent workspace vacancy.
        </p>
      </div>

      {/* Top Gauge & Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div className="lg:col-span-2 bg-white border border-gray-200 rounded-xl p-5 shadow-xs flex flex-col justify-between">
          <div>
            <h4 className="text-sm font-semibold text-gray-900 mb-1">Primary Scorecard C</h4>
            <p className="text-xs text-gray-500">Occupancy & utilization composite score</p>
          </div>
          <RadialGaugeChart
            score={score}
            title="Occupancy & Utilization"
            minVal={0}
            maxVal={100}
            unit="/100"
            height="260px"
          />
          <p className="text-xs text-gray-500 text-center mt-2">
            Reflects real estate efficiency without pressuring desk presence.
          </p>
        </div>

        <div className="lg:col-span-3 space-y-4">
          <h4 className="text-sm font-semibold text-gray-900">Spatial Presence Breakdown (Pod Aggregate)</h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <MetricCard
              label="Workstation Occupancy Rate (WOR)"
              value={`${wor.toFixed(1)}%`}
              delta="Target (65-85%)"
              deltaType="normal"
              caption="Active physical utilization during operational hours."
              icon={<Building2 className="w-4 h-4 text-blue-600" />}
            />

            <MetricCard
              label="Space Rightsizing Potential"
              value={`${Math.max(0.0, 100.0 - wor).toFixed(1)}%`}
              delta="Available Capacity"
              deltaType="normal"
              caption="Unallocated capacity available for flexible desk sharing."
            />

            <MetricCard
              label="Away-Time Ratio"
              value={`${away.toFixed(1)}%`}
              caption="Percentage of shift time occupants spend away from assigned desks."
            />

            <MetricCard
              label="Transitory Debounce Duration"
              value="5.0 mins"
              delta="Filter Applied"
              deltaType="normal"
              caption="Absences < 5 mins do not trigger vacancy states."
            />
          </div>
        </div>
      </div>

      {/* Person-Wise Workstation Presence Table */}
      <div className="space-y-3">
        <div>
          <h4 className="text-sm font-semibold text-gray-900">👤 Person-Wise Workstation Presence & Dwell Times</h4>
          <p className="text-xs text-gray-500">
            Individual presence ratios and continuous dwell intervals per ephemeral track (<code className="text-blue-600 font-mono bg-blue-50 px-1 rounded">TRK-xxxx</code>). Informs capacity planning without identifying individuals.
          </p>
        </div>
        <DataTable columns={columns} data={personPresenceData} />
      </div>

      {/* Zone Utilization Matrix & Hourly Trend with Variance */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-xs space-y-2">
          <h4 className="text-sm font-semibold text-gray-900">🪑 Workstation Zone Utilization Matrix</h4>
          <BarChart zones={zones.length > 0 ? zones : fallbackZones} height="280px" />
        </div>

        <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-xs space-y-2">
          <h4 className="text-sm font-semibold text-gray-900">📈 Hourly Occupancy Trend & Confidence Variance</h4>
          <TrendVarianceChart hours={shiftHours} occupancyRates={shiftRates} height="280px" />
        </div>
      </div>

      {/* Space Planning Guidance Card */}
      <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-xs space-y-2">
        <h4 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
          <Lightbulb className="w-4 h-4 text-amber-500" />
          <span>Space Planning Guidance (Rule REC-01)</span>
        </h4>
        {rec01 ? (
          <div className="space-y-2 text-xs">
            <p className="text-gray-800"><b>Hypothesis:</b> {rec01.hypothesis}</p>
            <p className="text-gray-500"><b>Observed Evidence:</b> {rec01.observed_metric_evidence}</p>
            <div className="p-3 bg-blue-50 border border-blue-200 text-blue-800 rounded-lg">
              <b>Recommended Facility Action:</b> {rec01.recommended_action}
            </div>
          </div>
        ) : (
          <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-lg flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>Space utilization is well-balanced within the 65%–85% target threshold.</span>
          </div>
        )}
      </div>
    </div>
  );
};
