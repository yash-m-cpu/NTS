import React, { useState, useEffect } from 'react';
import { AlertCircle, RefreshCw, VideoOff } from 'lucide-react';
import type { CameraId } from '../../types';
import { apiService } from '../../services/api';

interface LiveVideoPlayerProps {
  cameraId: CameraId;
  isAlive: boolean;
  onRefresh?: () => void;
}

export const LiveVideoPlayer: React.FC<LiveVideoPlayerProps> = ({
  cameraId,
  isAlive,
  onRefresh
}) => {
  const [streamError, setStreamError] = useState(false);
  const [streamKey, setStreamKey] = useState(Date.now());

  const streamUrl = `${apiService.getStreamUrl(cameraId)}?t=${streamKey}`;

  useEffect(() => {
    setStreamError(false);
    setStreamKey(Date.now());
  }, [cameraId, isAlive]);

  const handleRetry = () => {
    setStreamError(false);
    setStreamKey(Date.now());
    if (onRefresh) onRefresh();
  };

  if (!isAlive) {
    return (
      <div className="w-full aspect-video max-h-[520px] bg-slate-900/90 border border-slate-800 rounded-xl flex flex-col items-center justify-center p-6 text-center text-slate-400">
        <div className="w-16 h-16 rounded-full bg-slate-800 flex items-center justify-center mb-3 text-slate-500">
          <VideoOff className="w-8 h-8" />
        </div>
        <h4 className="text-base font-semibold text-slate-300">CCTV Stream Inactive</h4>
        <p className="text-xs text-slate-400 mt-1 max-w-md">
          Perception worker for <code className="text-slate-300 font-mono bg-slate-800 px-1.5 py-0.5 rounded">{cameraId}</code> is currently standby or paused.
        </p>
        <p className="text-xs text-slate-500 mt-2">
          Click <b>"Start Ingestion"</b> above to activate live inference and MJPEG streaming.
        </p>
      </div>
    );
  }

  if (streamError) {
    return (
      <div className="w-full aspect-video max-h-[520px] bg-slate-900/90 border border-rose-900/40 rounded-xl flex flex-col items-center justify-center p-6 text-center text-slate-300">
        <div className="w-14 h-14 rounded-full bg-rose-950/60 border border-rose-500/30 flex items-center justify-center mb-3 text-rose-400">
          <AlertCircle className="w-7 h-7" />
        </div>
        <h4 className="text-base font-semibold text-rose-300">Stream Connection Interrupted</h4>
        <p className="text-xs text-slate-400 mt-1 max-w-sm">
          Failed to load live multipart MJPEG frames from the backend server.
        </p>
        <button
          onClick={handleRetry}
          className="mt-4 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-900/60 hover:bg-rose-800 text-rose-200 text-xs font-medium transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Reconnect Stream</span>
        </button>
      </div>
    );
  }

  return (
    <div className="relative w-full aspect-video max-h-[540px] bg-black rounded-xl overflow-hidden border border-slate-800 shadow-lg flex items-center justify-center">
      {/* Live Badge */}
      <div className="absolute top-3 left-3 z-10 flex items-center gap-2 px-2.5 py-1 rounded-md bg-black/75 backdrop-blur-sm border border-slate-700/60 text-xs font-mono">
        <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
        <span className="font-semibold text-slate-200 uppercase tracking-wider">{cameraId} LIVE</span>
      </div>

      <img
        src={streamUrl}
        alt={`Live Feed ${cameraId}`}
        onError={() => setStreamError(true)}
        className="w-full h-full object-contain"
      />
    </div>
  );
};
