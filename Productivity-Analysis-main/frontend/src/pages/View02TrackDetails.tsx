import React, { useEffect, useState } from 'react';
import { useApp } from '../context/AppContext';
import { apiService } from '../services/api';
import type { ActiveTrack, LiveTelemetrySnapshot } from '../types';
import { MetricCard } from '../components/common/MetricCard';
import { RadialGaugeChart } from '../components/charts/RadialGaugeChart';
import { StackedBarChart } from '../components/charts/StackedBarChart';
import { DataTable, type Column } from '../components/common/DataTable';
import { ShieldCheck, UserCheck, Clock, Navigation, AlertCircle } from 'lucide-react';

const DEMO_TRACKS: ActiveTrack[] = [
  {
    track_id: 'TRK-0101',
    zone_id: 'ZONE-POD-01 (Desk A-01)',
    activity: 'ACT-01: Seated at Workstation',
    confidence: 0.94,
    velocity: 0.005,
    dwell_duration_seconds: 1420.0,
    transitions_count: 2,
    interruption_events: 1,
    waiting_seconds: 45.0,
    activity_breakdown: {
      'ACT-01': 68.0,
      'ACT-02': 12.0,
      'ACT-03': 8.0,
      'ACT-04': 7.0,
      'ACT-05': 3.0,
      'ACT-06': 1.0,
      'ACT-07': 1.0
    }
  },
  {
    track_id: 'TRK-0102',
    zone_id: 'ZONE-POD-01 (Desk A-02)',
    activity: 'ACT-01: Seated at Workstation',
    confidence: 0.91,
    velocity: 0.008,
    dwell_duration_seconds: 980.0,
    transitions_count: 3,
    interruption_events: 2,
    waiting_seconds: 30.0,
    activity_breakdown: {
      'ACT-01': 62.0,
      'ACT-02': 15.0,
      'ACT-03': 10.0,
      'ACT-04': 8.0,
      'ACT-05': 3.0,
      'ACT-06': 1.0,
      'ACT-07': 1.0
    }
  },
  {
    track_id: 'TRK-0103',
    zone_id: 'ZONE-POD-02 (Desk B-01)',
    activity: 'ACT-04: Workstation Interaction',
    confidence: 0.89,
    velocity: 0.018,
    dwell_duration_seconds: 640.0,
    transitions_count: 4,
    interruption_events: 0,
    waiting_seconds: 60.0,
    activity_breakdown: {
      'ACT-01': 54.0,
      'ACT-02': 18.0,
      'ACT-03': 12.0,
      'ACT-04': 10.0,
      'ACT-05': 4.0,
      'ACT-06': 1.0,
      'ACT-07': 1.0
    }
  },
  {
    track_id: 'TRK-0104',
    zone_id: 'ZONE-CORRIDOR-01',
    activity: 'ACT-03: Walking / In Transit',
    confidence: 0.92,
    velocity: 0.042,
    dwell_duration_seconds: 15.0,
    transitions_count: 6,
    interruption_events: 1,
    waiting_seconds: 12.0,
    activity_breakdown: {
      'ACT-01': 35.0,
      'ACT-02': 20.0,
      'ACT-03': 30.0,
      'ACT-04': 5.0,
      'ACT-05': 6.0,
      'ACT-06': 2.0,
      'ACT-07': 2.0
    }
  }
];

export const View02TrackDetails: React.FC = () => {
  const { selectedCamera } = useApp();
  const [telemetry, setTelemetry] = useState<LiveTelemetrySnapshot | null>(null);
  const [selectedTrackId, setSelectedTrackId] = useState<string>('TRK-0101');

  useEffect(() => {
    const fetchTelemetry = async () => {
      const data = await apiService.getLiveTelemetry(selectedCamera);
      setTelemetry(data);
    };

    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, 2000);
    return () => clearInterval(interval);
  }, [selectedCamera]);

  const activeTracks: ActiveTrack[] =
    telemetry?.active_tracks && telemetry.active_tracks.length > 0
      ? telemetry.active_tracks
      : DEMO_TRACKS;

  const currentTrack: ActiveTrack =
    activeTracks.find((t) => t.track_id === selectedTrackId) || activeTracks[0] || DEMO_TRACKS[0];

  const breakdown = currentTrack.activity_breakdown || {
    'ACT-01': 70.0,
    'ACT-02': 15.0,
    'ACT-03': 10.0,
    'ACT-05': 3.0,
    'ACT-07': 2.0
  };

  const getShare = (bd: Record<string, number>, code: string): number => {
    if (!bd) return 0.0;
    if (code in bd) return Number(bd[code]);
    for (const [k, v] of Object.entries(bd)) {
      if (k.startsWith(code)) return Number(v);
    }
    return 0.0;
  };

  let deskPresencePct = Number(
    (getShare(breakdown, 'ACT-01') + getShare(breakdown, 'ACT-02') + getShare(breakdown, 'ACT-04')).toFixed(1)
  );

  if (deskPresencePct <= 0.0 && getShare(breakdown, 'ACT-05') > 0) {
    deskPresencePct = Number(
      (100.0 - getShare(breakdown, 'ACT-06') - getShare(breakdown, 'ACT-07')).toFixed(1)
    );
  }
  deskPresencePct = Math.min(100.0, Math.max(0.0, deskPresencePct));

  const dwellSeconds = currentTrack.dwell_duration_seconds || 0;
  const dwellMins = dwellSeconds / 60.0;

  // Posture Table Rows
  const postureData = [
    { code: 'ACT-01', state: 'Seated at Workstation', share: `${getShare(breakdown, 'ACT-01').toFixed(1)}%`, status: 'Optimal focus posture' },
    { code: 'ACT-02', state: 'Standing at Workstation', share: `${getShare(breakdown, 'ACT-02').toFixed(1)}%`, status: 'Dynamic sit-stand' },
    { code: 'ACT-03', state: 'Walking / In Transit', share: `${getShare(breakdown, 'ACT-03').toFixed(1)}%`, status: 'Circulation mobility' },
    { code: 'ACT-04', state: 'Workstation Interaction', share: `${getShare(breakdown, 'ACT-04').toFixed(1)}%`, status: 'Active reaching / typing' },
    { code: 'ACT-05', state: 'Active Collaboration', share: `${getShare(breakdown, 'ACT-05').toFixed(1)}%`, status: 'Consultation / shared desk visit' },
    { code: 'ACT-06', state: 'Away from Monitored Desk', share: `${getShare(breakdown, 'ACT-06').toFixed(1)}%`, status: 'Common area / break' },
    { code: 'ACT-07', state: 'Unknown / Occluded', share: `${getShare(breakdown, 'ACT-07').toFixed(1)}%`, status: 'Camera angle occlusion' }
  ];

  const columns: Column<typeof postureData[0]>[] = [
    { header: 'Activity Code', accessorKey: 'code', className: 'font-mono text-sky-400 font-medium' },
    { header: 'Posture State', accessorKey: 'state' },
    { header: 'Individual Share (%)', accessorKey: 'share', className: 'font-mono font-semibold' },
    { header: 'Ergonomic Classification', accessorKey: 'status' }
  ];

  const isLive = Boolean(telemetry?.active_tracks && telemetry.active_tracks.length > 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
          <span>👤 View 02: Ephemeral Track Details Panel</span>
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Inspect active trajectory behavior, spatial friction, and ergonomic postures in real-time.
          Strictly bounded by privacy covenants: identifiers are non-reversible daily salted hashes.
        </p>
      </div>

      {!isLive && (
        <div className="p-3 bg-sky-950/40 border border-sky-500/20 rounded-xl text-xs text-sky-300 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-sky-400" />
          <span>No live tracks detected in camera feed right now. Displaying active demonstration session tracks below.</span>
        </div>
      )}

      {/* Track Selector & ID Card */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <label htmlFor="track-select" className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Select Active Ephemeral Track:
            </label>
            <select
              id="track-select"
              value={currentTrack.track_id}
              onChange={(e) => setSelectedTrackId(e.target.value)}
              className="bg-slate-950 border border-slate-700 text-sky-300 font-mono text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:border-sky-500"
            >
              {activeTracks.map((t) => (
                <option key={t.track_id} value={t.track_id}>
                  {t.track_id} — {t.activity.split(':')[0]} ({t.zone_id || 'Unmonitored'})
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Identity & Current Status Bar */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-3 border-t border-slate-800/80">
          <div>
            <span className="text-xs font-mono font-bold text-sky-400 text-base">{currentTrack.track_id}</span>
            <p className="text-[11px] text-slate-500 mt-0.5">Ephemeral Salted Hash (Rotated 00:00 UTC)</p>
            <p className="text-xs text-slate-300 mt-1">
              Assigned Zone: <code className="text-slate-200 font-mono bg-slate-950 px-1 rounded">{currentTrack.zone_id || 'Common'}</code>
            </p>
            <div className="mt-2 inline-block px-2.5 py-1 rounded bg-sky-900/60 border border-sky-500/30 text-sky-200 text-xs font-semibold">
              {currentTrack.activity}
            </div>
          </div>

          <MetricCard
            label="Personal Interruptions"
            value={`${currentTrack.interruption_events} events`}
            delta={`${Math.max(0.2, currentTrack.interruption_events * 0.8).toFixed(1)} / hr`}
            deltaType={currentTrack.interruption_events <= 2 ? 'normal' : 'inverse'}
            caption="Peer approaches while seated in focus posture."
            icon={<UserCheck className="w-4 h-4 text-emerald-400" />}
          />

          <MetricCard
            label="Service Waiting Time"
            value={`${currentTrack.waiting_seconds.toFixed(0)} sec`}
            delta={`${((currentTrack.waiting_seconds / Math.max(1, currentTrack.dwell_duration_seconds)) * 100).toFixed(1)}% of time`}
            deltaType="normal"
            caption="Stationary dwell in corridor or shared resource queues."
            icon={<Clock className="w-4 h-4 text-amber-400" />}
          />

          <MetricCard
            label="Zone Transit Churn"
            value={`${currentTrack.transitions_count} moves`}
            delta={`${Math.max(1.0, currentTrack.transitions_count * 1.5).toFixed(1)} moves/hr`}
            deltaType={currentTrack.transitions_count <= 5 ? 'normal' : 'inverse'}
            caption="Circulation movements between defined spatial zones."
            icon={<Navigation className="w-4 h-4 text-sky-400" />}
          />
        </div>
      </div>

      {/* Radial Gauge & Posture Stacked Bar */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div className="lg:col-span-2 bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-sm flex flex-col justify-between">
          <div>
            <h4 className="text-sm font-semibold text-slate-200 mb-1">🪑 Workstation Presence Ratio</h4>
            <p className="text-xs text-slate-400 mb-2">Physical occupancy ratio at monitored workstation</p>
          </div>
          <RadialGaugeChart
            score={deskPresencePct}
            title="Presence Ratio"
            minVal={0}
            maxVal={100}
            unit="%"
            height="240px"
          />
          <p className="text-xs text-slate-400 text-center mt-2 font-mono">
            Active desk presence: <b className="text-emerald-400">{deskPresencePct.toFixed(1)}%</b> | Focus dwell: <b className="text-sky-300">{dwellMins.toFixed(1)} min</b> ({Math.floor(dwellSeconds)}s)
          </p>
        </div>

        <div className="lg:col-span-3 bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-sm flex flex-col justify-between">
          <div>
            <h4 className="text-sm font-semibold text-slate-200 mb-1">
              📊 <code className="font-mono text-sky-400">{currentTrack.track_id}</code> Ergonomic Posture Breakdown
            </h4>
            <p className="text-xs text-slate-400 mb-3">Calculated strictly over active session frames for this individual track.</p>
          </div>
          <StackedBarChart activityShares={breakdown} height="200px" />
          <p className="text-[11px] text-slate-500 text-right mt-1">100% normalized across 7 biomechanical activity classes</p>
        </div>
      </div>

      {/* Individual Posture Data Table */}
      <div className="space-y-3">
        <h4 className="text-sm font-semibold text-slate-200">Personal Posture Shares & Ergonomic Balance</h4>
        <DataTable columns={columns} data={postureData} />
      </div>

      {/* Anti-Surveillance Guarantees */}
      <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-5 space-y-3">
        <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>Anti-Surveillance & Privacy Guarantees</span>
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800/80">
            <span className="font-semibold text-slate-200 block mb-1">🚫 Zero Facial Recognition</span>
            <p className="text-slate-400">Headless boundary tracking only. Face detection and biometric identification models are permanently banned.</p>
          </div>
          <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800/80">
            <span className="font-semibold text-slate-200 block mb-1">🔒 Ephemeral Session Hash</span>
            <p className="text-slate-400">Track IDs are irreversibly salted with daily random entropy and wiped every 24 hours. No cross-day tracking.</p>
          </div>
          <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800/80">
            <span className="font-semibold text-slate-200 block mb-1">⚖️ No Punitive Ranking</span>
            <p className="text-slate-400">Individual productivity scoring is prohibited. Metrics describe workspace ergonomic affordances, not employee value.</p>
          </div>
        </div>
      </div>
    </div>
  );
};
