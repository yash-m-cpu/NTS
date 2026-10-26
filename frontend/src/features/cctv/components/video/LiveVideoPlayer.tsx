import React, { useState, useEffect } from 'react';
import { AlertCircle, RefreshCw, VideoOff } from 'lucide-react';
import type { CameraId } from '../../types';
import { cctvApi } from '../../../../services/cctvApi';

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

  const streamUrl = `${cctvApi.getStreamUrl(cameraId)}?t=${streamKey}`;

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
      <div className="w-full aspect-video max-h-[520px] bg-white border border-gray-200 rounded-xl flex flex-col items-center justify-center p-6 text-center text-gray-500 shadow-sm">
        <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mb-3 text-gray-400">
          <VideoOff className="w-8 h-8" />
        </div>
        <h4 className="text-base font-semibold text-gray-800">CCTV Stream Standby</h4>
        <p className="text-xs text-gray-500 mt-1 max-w-md">
          Perception worker for <code className="text-blue-600 font-mono bg-blue-50 px-1.5 py-0.5 rounded">{cameraId}</code> is currently standby or paused.
        </p>
        <p className="text-xs text-gray-600 mt-2">
          Click <b>"Start Ingestion"</b> above to activate live inference and streaming.
        </p>
      </div>
    );
  }

  if (streamError) {
    return (
      <div className="w-full aspect-video max-h-[520px] bg-red-50 border border-red-200 rounded-xl flex flex-col items-center justify-center p-6 text-center text-red-800 shadow-sm">
        <div className="w-14 h-14 rounded-full bg-red-100 border border-red-200 flex items-center justify-center mb-3 text-red-600">
          <AlertCircle className="w-7 h-7" />
        </div>
        <h4 className="text-base font-semibold text-red-800">Stream Connection Interrupted</h4>
        <p className="text-xs text-red-600 mt-1 max-w-sm">
          Failed to load live multipart MJPEG frames from the CCTV backend. Ensure backend is running on port 8001.
        </p>
        <button
          onClick={handleRetry}
          className="mt-4 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-700 text-white text-xs font-medium transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Reconnect Stream</span>
        </button>
      </div>
    );
  }

  return (
    <div className="relative w-full aspect-video max-h-[540px] bg-black rounded-xl overflow-hidden border border-gray-300 shadow-md flex items-center justify-center">
      {/* Live Badge */}
      <div className="absolute top-3 left-3 z-10 flex items-center gap-2 px-2.5 py-1 rounded-md bg-black/75 backdrop-blur-sm border border-gray-700 text-xs font-mono">
        <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
        <span className="font-semibold text-white uppercase tracking-wider">{cameraId} LIVE</span>
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
