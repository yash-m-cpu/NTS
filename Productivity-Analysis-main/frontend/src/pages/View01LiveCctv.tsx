import React, { useEffect, useState } from 'react';
import {
  Play,
  Square,
  Upload,
  Layers,
  ShieldAlert,
  Activity,
  User,
  Radio,
  CheckCircle2
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { apiService } from '../services/api';
import type { SessionStatus } from '../types';
import { MetricCard } from '../components/common/MetricCard';
import { LiveVideoPlayer } from '../components/video/LiveVideoPlayer';

export const View01LiveCctv: React.FC = () => {
  const { selectedCamera, setIsUploadModalOpen, activeAnalyzedVideo } = useApp();
  const [status, setStatus] = useState<SessionStatus | null>(null);
  const [loadingAction, setLoadingAction] = useState<boolean>(false);

  // LOD layer toggles
  const [lodZones, setLodZones] = useState<boolean>(true);
  const [lodBoxes, setLodBoxes] = useState<boolean>(true);
  const [lodFeet, setLodFeet] = useState<boolean>(true);
  const [lodBadges, setLodBadges] = useState<boolean>(true);
  const [lodPills, setLodPills] = useState<boolean>(true);

  const fetchStatus = async () => {
    const s = await apiService.getSessionStatus(selectedCamera);
    setStatus(s);
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 1500);
    return () => clearInterval(interval);
  }, [selectedCamera]);

  const handleStart = async () => {
    setLoadingAction(true);
    try {
      await apiService.startSession(selectedCamera);
      await fetchStatus();
    } finally {
      setLoadingAction(false);
    }
  };

  const handleStop = async () => {
    setLoadingAction(true);
    try {
      await apiService.stopSession(selectedCamera);
      await fetchStatus();
    } finally {
      setLoadingAction(false);
    }
  };

  const isAlive = status?.is_alive ?? false;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
          <span>📹 View 01: Live Annotated CCTV Stream</span>
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Real-time visual verification of spatial zone occupancy, person detection, and pseudonymized trajectory tracking.
          Overlays conform to strict privacy boundaries.
        </p>
      </div>

      {/* Upload Banner / Trigger */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-sky-950/60 border border-sky-500/20 text-sky-400">
            <Upload className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-200">Custom Workplace Video Feed</h4>
            <p className="text-xs text-slate-400">
              {activeAnalyzedVideo ? (
                <span>Currently analyzing: <b className="text-sky-300 font-mono">{activeAnalyzedVideo}</b></span>
              ) : (
                'Upload a CCTV recording (.mp4, .avi, .mov) to bind directly to the inference engine.'
              )}
            </p>
          </div>
        </div>
        <button
          onClick={() => setIsUploadModalOpen(true)}
          className="px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold rounded-lg shadow-sm transition-colors flex items-center gap-2"
        >
          <Upload className="w-4 h-4" />
          <span>Upload Video</span>
        </button>
      </div>

      {/* Ingestion Controls & Top Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Pipeline Start/Stop */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
          <span className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
            Pipeline Control
          </span>
          {!isAlive ? (
            <button
              onClick={handleStart}
              disabled={loadingAction}
              className="w-full py-2.5 px-4 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-bold rounded-lg shadow flex items-center justify-center gap-2 transition-colors"
            >
              <Play className="w-4 h-4 fill-white" />
              <span>Start Ingestion</span>
            </button>
          ) : (
            <button
              onClick={handleStop}
              disabled={loadingAction}
              className="w-full py-2.5 px-4 bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white text-xs font-bold rounded-lg shadow flex items-center justify-center gap-2 transition-colors"
            >
              <Square className="w-4 h-4 fill-white" />
              <span>Stop Ingestion</span>
            </button>
          )}
          <span className="text-[11px] text-slate-500 mt-2">
            Target camera: <code className="text-slate-300 font-mono">{selectedCamera}</code>
          </span>
        </div>

        <MetricCard
          label="Connection Status"
          value={isAlive ? 'ONLINE' : 'STOPPED'}
          delta={isAlive ? 'Streaming' : 'Standby'}
          deltaType={isAlive ? 'normal' : 'off'}
          caption="Hardware capture / MJPEG worker state."
          icon={<Radio className="w-4 h-4 text-sky-400" />}
        />

        <MetricCard
          label="Inference Rate"
          value={`${(status?.fps ?? 0.0).toFixed(1)} FPS`}
          delta="Real-time"
          deltaType="normal"
          caption="Computer vision detection & tracking rate."
          icon={<Activity className="w-4 h-4 text-emerald-400" />}
        />

        <MetricCard
          label="Active Tracks"
          value={`${status?.active_tracks_count ?? 0} persons`}
          delta="Active"
          deltaType="normal"
          caption="Simultaneous pseudonymized trajectories."
          icon={<User className="w-4 h-4 text-amber-400" />}
        />
      </div>

      {/* Video Stream & Overlay Controls */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Main Video Stream Container (3 cols) */}
        <div className="lg:col-span-3">
          <LiveVideoPlayer
            cameraId={selectedCamera}
            isAlive={isAlive}
            onRefresh={fetchStatus}
          />
        </div>

        {/* Controls Column (1 col) */}
        <div className="space-y-4">
          <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
            <div className="flex items-center gap-2 text-slate-200 border-b border-slate-800 pb-2">
              <Layers className="w-4 h-4 text-sky-400" />
              <h3 className="text-sm font-semibold">Overlay Controls</h3>
            </div>
            <p className="text-xs text-slate-400">Level-of-Detail (LOD) Layer Toggles</p>

            <div className="space-y-2.5 text-xs text-slate-300">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={lodZones}
                  onChange={(e) => setLodZones(e.target.checked)}
                  className="rounded border-slate-700 bg-slate-800 text-sky-500 focus:ring-0"
                />
                <span>Workstation Polygons</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={lodBoxes}
                  onChange={(e) => setLodBoxes(e.target.checked)}
                  className="rounded border-slate-700 bg-slate-800 text-sky-500 focus:ring-0"
                />
                <span>Person Bounding Boxes</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={lodFeet}
                  onChange={(e) => setLodFeet(e.target.checked)}
                  className="rounded border-slate-700 bg-slate-800 text-sky-500 focus:ring-0"
                />
                <span>Ground Footprints</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={lodBadges}
                  onChange={(e) => setLodBadges(e.target.checked)}
                  className="rounded border-slate-700 bg-slate-800 text-sky-500 focus:ring-0"
                />
                <span>Salted Track Badges</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={lodPills}
                  onChange={(e) => setLodPills(e.target.checked)}
                  className="rounded border-slate-700 bg-slate-800 text-sky-500 focus:ring-0"
                />
                <span>Activity State Pills</span>
              </label>
            </div>
          </div>

          <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm space-y-3">
            <div className="flex items-center gap-2 text-slate-200 border-b border-slate-800 pb-2">
              <ShieldAlert className="w-4 h-4 text-emerald-400" />
              <h3 className="text-sm font-semibold">Privacy Guard</h3>
            </div>
            <p className="text-xs text-slate-300 font-semibold flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>Facial Recognition Ban Active</span>
            </p>
            <p className="text-xs text-slate-400 leading-relaxed">
              All faces are unmapped and strictly excluded. Tracks use ephemeral hashes (<code className="text-sky-300 font-mono">TRK-xxxx</code>) rotated daily at 00:00 UTC.
            </p>
          </div>
        </div>
      </div>

      {/* Stream Health Metrics Footer */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 rounded-xl bg-slate-900/80 border border-slate-800 text-xs">
        <div>
          <span className="text-slate-400">Camera Target:</span>{' '}
          <code className="text-slate-200 font-mono bg-slate-800 px-1.5 py-0.5 rounded">{selectedCamera}</code>
        </div>
        <div>
          <span className="text-slate-400">Frames Ingested:</span>{' '}
          <b className="text-slate-200 font-mono">{status?.total_frames_processed ?? 0}</b>
        </div>
        <div>
          <span className="text-slate-400">Dropped Frames:</span>{' '}
          <b className="text-slate-200 font-mono">{status?.dropped_frames_count ?? 0}</b>
        </div>
        <div>
          <span className="text-slate-400">Observation Coverage:</span>{' '}
          <b className="text-slate-200 font-mono">{(status?.observation_coverage_pct ?? 0.0).toFixed(1)}%</b>
        </div>
      </div>
    </div>
  );
};
