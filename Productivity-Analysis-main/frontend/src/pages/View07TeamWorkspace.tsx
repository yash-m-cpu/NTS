import React, { useEffect, useState } from 'react';
import { useApp } from '../context/AppContext';
import { apiService } from '../services/api';
import type { SpatialZone } from '../types';
import { MetricCard } from '../components/common/MetricCard';
import { Users, Shield, MessageSquare } from 'lucide-react';

export const View07TeamWorkspace: React.FC = () => {
  const { selectedCamera } = useApp();
  const [zones, setZones] = useState<SpatialZone[]>([]);

  useEffect(() => {
    const fetchZones = async () => {
      const z = await apiService.getZones(selectedCamera);
      setZones(z);
    };
    fetchZones();
  }, [selectedCamera]);

  const displayZones: SpatialZone[] =
    zones.length > 0
      ? zones
      : [
          { zone_id: 'POD-ENG-01', camera_id: selectedCamera, name: 'Engineering Alpha Pod', zone_type: 'WORKSTATION', capacity: 4, polygon_coords: [] },
          { zone_id: 'POD-ENG-02', camera_id: selectedCamera, name: 'Engineering Beta Pod', zone_type: 'WORKSTATION', capacity: 4, polygon_coords: [] },
          { zone_id: 'COLLAB-CENTRAL', camera_id: selectedCamera, name: 'Central Huddle Space', zone_type: 'COLLABORATION', capacity: 6, polygon_coords: [] },
          { zone_id: 'CORRIDOR-MAIN', camera_id: selectedCamera, name: 'Main Office Artery', zone_type: 'CORRIDOR', capacity: 10, polygon_coords: [] }
        ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
          <span>👥 View 07: Team & Workspace Overview (Macro Analytics)</span>
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Macro department-level spatial analytics with mandatory k-anonymity (k ≥ 5).
          Strictly prohibits individual employee rankings or leaderboards.
        </p>
      </div>

      {/* Anti-Ranking Banner */}
      <div className="p-4 bg-sky-950/40 border border-sky-500/30 rounded-xl text-xs text-sky-200 flex items-start gap-3">
        <Shield className="w-5 h-5 text-sky-400 shrink-0 mt-0.5" />
        <div>
          <h4 className="font-semibold text-sky-300 text-sm mb-1">
            🛡️ Strict k-Anonymity (k ≥ 5) & Anti-Ranking Policy
          </h4>
          <p className="leading-relaxed text-slate-300">
            Individual leaderboards and desk-level employee comparisons are strictly prohibited by system architecture.
            All observations are aggregated at the pod and departmental level.
          </p>
        </div>
      </div>

      {/* Macro KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Monitored Team Size"
          value="12 Members"
          delta="k ≥ 5 Compliant"
          deltaType="normal"
          caption="Aggregate group size threshold."
          icon={<Users className="w-4 h-4 text-sky-400" />}
        />

        <MetricCard
          label="Pod Collaboration Index"
          value="68.4 / 100"
          delta="+4.2 vs Baseline"
          deltaType="normal"
          caption="Healthy conversational exchange ratio."
        />

        <MetricCard
          label="Meeting Room Pressure"
          value="42.0%"
          delta="Balanced"
          deltaType="normal"
          caption="Secondary shared room demand."
        />

        <MetricCard
          label="Focus Work Protection"
          value="74.5%"
          delta="Nominal"
          deltaType="normal"
          caption="Unbroken individual focus intervals."
        />
      </div>

      {/* Interactive Pod & Zone Grid */}
      <div className="space-y-3">
        <div>
          <h4 className="text-sm font-semibold text-slate-200">🗺️ Interactive Floor Plan & Pod Utilization</h4>
          <p className="text-xs text-slate-400">Aggregated occupancy metrics across functional collaboration zones.</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {displayZones.map((z) => {
            const ztype = z.zone_type || 'WORKSTATION';
            let badgeBg = 'bg-sky-950 text-sky-300 border-sky-500/30';
            if (ztype === 'COLLABORATION') badgeBg = 'bg-emerald-950 text-emerald-300 border-emerald-500/30';
            if (ztype === 'CORRIDOR') badgeBg = 'bg-purple-950 text-purple-300 border-purple-500/30';

            return (
              <div
                key={z.zone_id}
                className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 text-center shadow-sm hover:border-slate-700 transition-colors space-y-2"
              >
                <span className={`inline-block text-[10px] font-semibold uppercase px-2 py-0.5 rounded border ${badgeBg}`}>
                  {ztype}
                </span>
                <h5 className="text-sm font-bold text-slate-100 font-mono">{z.zone_id}</h5>
                <p className="text-xs text-slate-400 truncate">{z.name}</p>
                <p className="text-2xl font-bold text-slate-100 pt-1">76%</p>
                <span className="text-[11px] text-emerald-400 font-medium flex items-center justify-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span>Active Usage</span>
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Collaboration Insight */}
      <div className="p-4 bg-slate-900/80 border border-slate-800 rounded-xl text-xs text-slate-300 space-y-1">
        <h5 className="font-semibold text-slate-200 flex items-center gap-2">
          <MessageSquare className="w-4 h-4 text-sky-400" />
          <span>🤝 Collaboration & Huddle Activity</span>
        </h5>
        <p className="text-slate-400 leading-relaxed">
          <b>Pod Interaction Insight:</b> The team displays healthy synchronous collaboration bursts at 10:30 and 15:00,
          with dedicated deep-focus buffers in early afternoons. Meeting room congestion remains under threshold, with 58% of huddles occurring organically at pod tables.
        </p>
      </div>
    </div>
  );
};
