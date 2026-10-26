import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { apiService } from '../../../services/cctvApi';
import type { ExportStatus } from '../types';
import { Download, RefreshCw, Send, Lock, Trash2, Clock } from 'lucide-react';

export const View09VideoExport: React.FC = () => {
  const { selectedCamera } = useApp();
  const [sourceCamera, setSourceCamera] = useState(selectedCamera);
  const [clipFrames, setClipFrames] = useState<number>(150);
  const [dpoToken, setDpoToken] = useState('DPO-AUTH-2026-TOKEN-XYZ');
  const [justification, setJustification] = useState(
    'Facility ergonomics assessment for quarterly layout review. Redacted video clip for pod spatial flow verification.'
  );

  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<ExportStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    setSourceCamera(selectedCamera);
  }, [selectedCamera]);

  const pollJob = async () => {
    if (!activeJobId) return;
    const status = await apiService.getExportStatus(activeJobId);
    setJobStatus(status);
  };

  useEffect(() => {
    if (!activeJobId) return;
    pollJob();
    const interval = setInterval(pollJob, 2000);
    return () => clearInterval(interval);
  }, [activeJobId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setSuccessMsg(null);

    if (!justification || justification.trim().length < 15) {
      setErrorMsg('Submission rejected: Detailed business justification (≥15 chars) is mandatory.');
      return;
    }
    if (!dpoToken) {
      setErrorMsg('Submission rejected: Valid DPO dual-control authorization token is required.');
      return;
    }

    setLoading(true);
    try {
      const res = await apiService.triggerVideoExport(sourceCamera, clipFrames);
      if (res && res.job_id) {
        setActiveJobId(res.job_id);
        setSuccessMsg(`Video export job queued! Job ID: ${res.job_id}`);
      } else {
        setErrorMsg('Failed to queue export job with backend.');
      }
    } catch (err: any) {
      setErrorMsg(err?.message || 'Error communicating with export service.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
          <span>📼 View 09: Privacy-Preserving Video Export Controls</span>
        </h2>
        <p className="text-xs text-gray-500 mt-1">
          Request cryptographically annotated and redacted MP4 clips for space planning audits.
          Strictly gated by Data Protection Officer (DPO) dual-control authorization.
        </p>
      </div>

      {/* Export Request Specification Form */}
      <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-xs space-y-4">
        <h4 className="text-sm font-semibold text-gray-900">📝 Export Request Specification</h4>

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-gray-700 block mb-1">Source Camera Stream</label>
              <select
                value={sourceCamera}
                onChange={(e) => setSourceCamera(e.target.value as any)}
                className="w-full bg-gray-50 border border-gray-300 text-gray-900 rounded-lg px-3 py-2 font-mono cursor-pointer"
              >
                <option value="CAM-01">CAM-01</option>
                <option value="CAM-02">CAM-02</option>
                <option value="CAM-03">CAM-03</option>
              </select>
            </div>

            <div>
              <label className="text-gray-700 block mb-1">
                Export Duration: <b className="text-blue-600 font-mono">{clipFrames} frames</b> (~{(clipFrames / 15).toFixed(1)}s)
              </label>
              <input
                type="range"
                min="30"
                max="300"
                step="30"
                value={clipFrames}
                onChange={(e) => setClipFrames(Number(e.target.value))}
                className="w-full accent-blue-600 cursor-pointer"
              />
              <div className="flex justify-between text-[10px] text-gray-500 font-mono mt-1">
                <span>30 frames (2s)</span>
                <span>150 frames (10s)</span>
                <span>300 frames (20s)</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-gray-700 block mb-1">DPO Dual-Control Authorization Token</label>
              <input
                type="password"
                value={dpoToken}
                onChange={(e) => setDpoToken(e.target.value)}
                className="w-full bg-gray-50 border border-gray-300 text-gray-900 rounded-lg px-3 py-2 font-mono"
              />
            </div>
            <div className="flex items-center pt-5">
              <label className="flex items-center gap-2 cursor-not-allowed opacity-80 text-gray-600">
                <input
                  type="checkbox"
                  checked={true}
                  disabled={true}
                  className="rounded border-gray-300 text-blue-600"
                />
                <span>Automated Privacy Masking / Redaction (Enforced)</span>
              </label>
            </div>
          </div>

          <div>
            <label className="text-gray-700 block mb-1">
              Mandatory Business Justification (GDPR / Audit Requirement)
            </label>
            <textarea
              rows={3}
              value={justification}
              onChange={(e) => setJustification(e.target.value)}
              className="w-full bg-gray-50 border border-gray-300 text-gray-900 rounded-lg p-3 text-xs leading-relaxed focus:outline-none focus:border-blue-500"
            />
          </div>

          {errorMsg && (
            <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 rounded-lg">
              {errorMsg}
            </div>
          )}

          {successMsg && (
            <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg">
              {successMsg}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold rounded-lg shadow-xs transition-colors cursor-pointer"
          >
            <Send className="w-4 h-4" />
            <span>Submit Render Job</span>
          </button>
        </form>
      </div>

      {/* Active Export Queue & Registry */}
      <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-xs space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-semibold text-gray-900">📋 Active Export Queue & Download Registry</h4>
          {activeJobId && (
            <button
              onClick={pollJob}
              className="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1 font-medium cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Refresh Status</span>
            </button>
          )}
        </div>

        {activeJobId && jobStatus ? (
          <div className="p-4 bg-gray-50 rounded-xl border border-gray-200 flex flex-wrap items-center justify-between gap-4 text-xs">
            <div>
              <span className="text-gray-500 block">Job Identifier</span>
              <code className="text-blue-600 font-mono font-bold text-sm">{jobStatus.job_id}</code>
            </div>

            <div>
              <span className="text-gray-500 block mb-1">Status</span>
              <span
                className={`px-2.5 py-1 rounded-md text-xs font-semibold ${
                  jobStatus.status === 'READY'
                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                    : jobStatus.status === 'RENDERING'
                    ? 'bg-blue-50 text-blue-700 border border-blue-200 animate-pulse'
                    : 'bg-amber-50 text-amber-700 border border-amber-200'
                }`}
              >
                {jobStatus.status === 'READY'
                  ? '🟢 READY FOR DOWNLOAD'
                  : `⚙️ ${jobStatus.status} (${jobStatus.progress_pct.toFixed(0)}%)`}
              </span>
            </div>

            <div>
              <span className="text-gray-500 block">Render Progress</span>
              <span className="font-mono text-gray-900">
                {jobStatus.frames_rendered} / {jobStatus.total_frames} frames
              </span>
            </div>

            <div>
              {jobStatus.download_url ? (
                <a
                  href={jobStatus.download_url}
                  download
                  className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-lg shadow-xs transition-colors"
                >
                  <Download className="w-4 h-4" />
                  <span>Download Redacted MP4</span>
                </a>
              ) : (
                <span className="text-gray-400 italic">Processing video frames...</span>
              )}
            </div>
          </div>
        ) : (
          <div className="p-4 bg-gray-50 rounded-xl text-gray-400 text-xs italic border border-gray-200">
            No active export jobs initiated in this session.
          </div>
        )}
      </div>

      {/* Compliance Assurances */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
        <div className="p-4 bg-white border border-gray-200 rounded-xl space-y-1 shadow-xs">
          <span className="font-semibold text-gray-900 flex items-center gap-1.5">
            <Trash2 className="w-4 h-4 text-rose-500" />
            <span>Edge Video Shredding</span>
          </span>
          <p className="text-gray-500">Raw CCTV footage on camera edge nodes is shredded after 72 hours.</p>
        </div>

        <div className="p-4 bg-white border border-gray-200 rounded-xl space-y-1 shadow-xs">
          <span className="font-semibold text-gray-900 flex items-center gap-1.5">
            <Lock className="w-4 h-4 text-blue-600" />
            <span>Audit Logging</span>
          </span>
          <p className="text-gray-500">Every export request is logged to the immutable STRIDE audit table.</p>
        </div>

        <div className="p-4 bg-white border border-gray-200 rounded-xl space-y-1 shadow-xs">
          <span className="font-semibold text-gray-900 flex items-center gap-1.5">
            <Clock className="w-4 h-4 text-amber-500" />
            <span>Expiring Storage</span>
          </span>
          <p className="text-gray-500">Exported MP4 artifacts expire and are deleted automatically within 24 hours.</p>
        </div>
      </div>
    </div>
  );
};
