import { useParams, Link } from 'react-router-dom';
import { useState, useEffect, useCallback } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { apiClient } from '../lib/apiClient';
import FeatureChart from '../components/FeatureChart';
import { ProsodyChart } from '../components/ProsodyChart';
import { ParticipationRadar } from '../components/ParticipationRadar';

interface ParticipantTrack {
  id: string;
  track_label: string;
  first_seen_at_ms: number;
  last_seen_at_ms: number;
  detection_frame_count: number;
  avg_detection_confidence: number | null;
}

interface FeatureResponse {
  id: string;
  participant_track_id: string;
  feature_type: string;
  timestamp_ms: number;
  values: {
    rotation?: { pitch: number; yaw: number; roll: number };
    emotions?: Record<string, number>;
    dominant_emotion?: string;
    gaze?: { bearing: number };
    keypoints?: any[];
    hands?: any[];
  };
}

interface SpeakingTurn { start: number; end: number; text: string; }
interface ParticipantSpeakingSummary {
  track_id: string; track_label: string;
  speaking_time_seconds: number | null; speech_ratio: number | null;
  turn_count: number | null; avg_turn_duration_seconds: number | null;
  turns: SpeakingTurn[];
}
interface InteractionEdge { from: string; to: string; exchanges: number; quick_responses: number; }
interface InteractionNode { id: string; track_id: string; speaking_time: number; }
interface InteractionGraph { nodes: InteractionNode[]; edges: InteractionEdge[]; }

// ---- Report types ----
interface NtsDimension {
  score: number | null;
  confidence: number | null;
  evidence: string[];
  limitations: string[];
}
interface NtsVisualProfile {
  communication: NtsDimension;
  teamwork: NtsDimension;
  leadership: NtsDimension;
  influence: NtsDimension;
  resilience_consistency: NtsDimension;
  decision_making: { score: null; status: string; reason: string };
}
interface VisualReport {
  participant_id: string;
  executive_summary: string;
  visual_profile: { head_movement: string; gaze: string; posture: string; hands_gestures: string; facial_affect: string };
  nts_visual_profile: NtsVisualProfile;
  strengths: string[];
  development_areas: string[];
  recommendations: string[];
  detailed_summary: string;
  limitations: string[];
}
interface ReportState {
  status: 'idle' | 'generating' | 'completed' | 'failed';
  report: VisualReport | null;
  pdf_available: boolean;
  error: string | null;
  report_id: string | null;
}

function formatTime(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}m ${s}s`;
}

// ---- NTS Score Badge ----
function ScoreBadge({ score }: { score: number | null }) {
  if (score === null) return <span className="text-xs text-gray-400 italic">Insufficient data</span>;
  const color = score >= 75 ? 'bg-green-100 text-green-800' : score >= 50 ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800';
  return <span className={`px-2 py-0.5 rounded text-xs font-semibold ${color}`}>{score}/100</span>;
}

// ---- Report Preview Panel ----
function ReportPanel({ report, meetingId, trackId, onRegenerate, pdfAvailable }:
  { report: VisualReport; meetingId: string; trackId: string; onRegenerate: () => void; pdfAvailable: boolean }) {
  const nts = report.nts_visual_profile;
  const NTS_DIMENSIONS = [
    { key: 'communication', label: 'Communication (Non-verbal)' },
    { key: 'teamwork', label: 'Teamwork (Visual)' },
    { key: 'leadership', label: 'Leadership (Visual)' },
    { key: 'influence', label: 'Influence (Visual)' },
    { key: 'resilience_consistency', label: 'Resilience Consistency' },
  ] as const;

  const handleDownloadPdf = async () => {
    const res = await apiClient(`/meetings/${meetingId}/tracks/${trackId}/report/pdf`);
    if (!res.ok) { alert('PDF download failed'); return; }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `nts_report_${trackId}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="mt-6 border border-blue-200 rounded-lg bg-blue-50/30 overflow-hidden">
      {/* Header */}
      <div className="bg-blue-700 text-white px-5 py-3 flex justify-between items-center">
        <div>
          <p className="font-bold text-sm">NTS Visual Behavioral Report</p>
          <p className="text-xs opacity-80">Visual-only analysis · Not a psychological assessment</p>
        </div>
        <div className="flex gap-2">
          {pdfAvailable && (
            <button onClick={handleDownloadPdf}
              className="bg-white text-blue-700 text-xs font-semibold px-3 py-1.5 rounded hover:bg-blue-50">
              ⬇ Download PDF
            </button>
          )}
          <button onClick={onRegenerate}
            className="bg-blue-600 border border-blue-300 text-white text-xs font-semibold px-3 py-1.5 rounded hover:bg-blue-500">
            ↺ Regenerate
          </button>
        </div>
      </div>

      <div className="p-5 space-y-6">
        {/* Executive Summary */}
        <section>
          <h3 className="font-semibold text-gray-800 mb-2 text-sm uppercase tracking-wide">Executive Summary</h3>
          {report.executive_summary.split('\n\n').map((p, i) => (
            <p key={i} className="text-sm text-gray-700 leading-relaxed mb-2">{p}</p>
          ))}
        </section>

        {/* Visual Profile */}
        <section>
          <h3 className="font-semibold text-gray-800 mb-2 text-sm uppercase tracking-wide">Visual Profile</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {Object.entries(report.visual_profile).map(([k, v]) => (
              <div key={k} className="bg-white rounded border p-3">
                <p className="text-xs font-semibold text-gray-500 uppercase mb-0.5">{k.replace(/_/g, ' ')}</p>
                <p className="text-sm text-gray-700">{v}</p>
              </div>
            ))}
          </div>
        </section>

        {/* NTS Visual Profile */}
        <section>
          <h3 className="font-semibold text-gray-800 mb-2 text-sm uppercase tracking-wide">NTS Visual Profile</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse bg-white rounded overflow-hidden">
              <thead className="bg-blue-700 text-white text-xs">
                <tr>
                  <th className="text-left px-3 py-2">Dimension</th>
                  <th className="px-3 py-2 text-center">Score</th>
                  <th className="px-3 py-2 text-center">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {NTS_DIMENSIONS.map(({ key, label }, i) => {
                  const dim = nts[key] as NtsDimension;
                  return (
                    <tr key={key} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                      <td className="px-3 py-2 font-medium text-gray-700">{label}</td>
                      <td className="px-3 py-2 text-center"><ScoreBadge score={dim.score} /></td>
                      <td className="px-3 py-2 text-center text-xs text-gray-500">
                        {dim.confidence != null ? `${Math.round(dim.confidence * 100)}%` : '—'}
                      </td>
                    </tr>
                  );
                })}
                <tr className="bg-gray-100">
                  <td className="px-3 py-2 font-medium text-gray-500">Decision-Making</td>
                  <td colSpan={2} className="px-3 py-2 text-center text-xs text-gray-400 italic">
                    Not Assessed (visual-only mode)
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          {/* Evidence */}
          {NTS_DIMENSIONS.map(({ key, label }) => {
            const dim = nts[key] as NtsDimension;
            if (!dim.evidence?.length) return null;
            return (
              <div key={key} className="mt-3">
                <p className="text-xs font-semibold text-gray-500 mb-1">{label} — Evidence</p>
                <ul className="list-disc list-inside space-y-0.5">
                  {dim.evidence.map((e, i) => <li key={i} className="text-xs text-gray-600">{e}</li>)}
                </ul>
              </div>
            );
          })}
        </section>

        {/* Strengths + Dev Areas side by side */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <section className="bg-green-50 border border-green-200 rounded p-4">
            <h3 className="font-semibold text-green-800 mb-2 text-sm">✓ Key Strengths</h3>
            <ul className="space-y-1">
              {report.strengths.map((s, i) => <li key={i} className="text-sm text-gray-700 flex gap-2"><span className="text-green-600 mt-0.5">•</span>{s}</li>)}
            </ul>
          </section>
          <section className="bg-amber-50 border border-amber-200 rounded p-4">
            <h3 className="font-semibold text-amber-800 mb-2 text-sm">△ Areas for Development</h3>
            <ul className="space-y-1">
              {report.development_areas.map((d, i) => <li key={i} className="text-sm text-gray-700 flex gap-2"><span className="text-amber-600 mt-0.5">•</span>{d}</li>)}
            </ul>
          </section>
        </div>

        {/* Recommendations */}
        <section className="bg-white border rounded p-4">
          <h3 className="font-semibold text-gray-800 mb-2 text-sm">→ Recommended Actions</h3>
          <ul className="space-y-1">
            {report.recommendations.map((r, i) => <li key={i} className="text-sm text-gray-700 flex gap-2"><span className="text-blue-600 mt-0.5">→</span>{r}</li>)}
          </ul>
        </section>

        {/* Detailed Summary */}
        <section>
          <h3 className="font-semibold text-gray-800 mb-2 text-sm uppercase tracking-wide">Detailed Summary</h3>
          {report.detailed_summary.split('\n\n').map((p, i) => (
            <p key={i} className="text-sm text-gray-700 leading-relaxed mb-2">{p}</p>
          ))}
        </section>

        {/* Limitations */}
        {report.limitations?.length > 0 && (
          <section className="bg-gray-50 border rounded p-3">
            <h3 className="font-semibold text-gray-600 mb-1 text-xs uppercase">Limitations & Disclaimer</h3>
            <ul className="space-y-0.5">
              {report.limitations.map((l, i) => <li key={i} className="text-xs text-gray-500">• {l}</li>)}
            </ul>
            <p className="text-xs text-gray-400 mt-2 italic">
              This report is derived from observable video-based features only and is NOT a psychological or personality assessment.
            </p>
          </section>
        )}
      </div>
    </div>
  );
}

// ---- Main Component ----
export default function MeetingAnalysis() {
  const { meetingId } = useParams<{ meetingId: string }>();
  const [tracks, setTracks] = useState<ParticipantTrack[]>([]);
  const [features, setFeatures] = useState<FeatureResponse[]>([]);
  const [metrics, setMetrics] = useState<any[]>([]);
  const [prosody, setProsody] = useState<any[]>([]);
  const [speakingSummary, setSpeakingSummary] = useState<ParticipantSpeakingSummary[]>([]);
  const [interactionGraph, setInteractionGraph] = useState<InteractionGraph | null>(null);
  const [selectedTrackId, setSelectedTrackId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'visual' | 'speech' | 'interaction' | 'report' | 'annotated'>('visual');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Per-track report state
  const [reportStates, setReportStates] = useState<Record<string, ReportState>>({});

  // Annotated video state
  const [annotatedVideoStatus, setAnnotatedVideoStatus] = useState<'not_requested' | 'queued' | 'running' | 'succeeded' | 'completed' | 'failed'>('not_requested');
  const [annotatedVideoUrl, setAnnotatedVideoUrl] = useState<string | null>(null);
  const [annotatedVideoError, setAnnotatedVideoError] = useState<string | null>(null);

  // Poll annotated video status while job is in-progress
  useEffect(() => {
    if (!meetingId) return;
    if (!['queued', 'running'].includes(annotatedVideoStatus)) return;
    const interval = setInterval(async () => {
      try {
        const res = await apiClient(`/meetings/${meetingId}/annotated-video`);
        if (res.ok) {
          const j = await res.json();
          const d = j.data;
          setAnnotatedVideoStatus(d.status || 'not_requested');
          if (d.annotated_video_url) setAnnotatedVideoUrl(d.annotated_video_url);
          if (d.error_message) setAnnotatedVideoError(d.error_message);
        }
      } catch (_) {}
    }, 5000);
    return () => clearInterval(interval);
  }, [meetingId, annotatedVideoStatus]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [tracksRes, featuresRes, speakingRes, graphRes, annotatedRes, metricsRes, prosodyRes] = await Promise.all([
          apiClient(`/meetings/${meetingId}/tracks`),
          apiClient(`/meetings/${meetingId}/features?limit=10000`),
          apiClient(`/meetings/${meetingId}/speaking-summary`).catch(() => null),
          apiClient(`/meetings/${meetingId}/interaction-graph`).catch(() => null),
          apiClient(`/meetings/${meetingId}/annotated-video`).catch(() => null),
          apiClient(`/meetings/${meetingId}/metrics`).catch(() => null),
          apiClient(`/meetings/${meetingId}/prosody`).catch(() => null),
        ]);

        if (!tracksRes.ok) throw new Error('Failed to fetch meeting tracks');
        if (!featuresRes.ok) throw new Error('Failed to fetch meeting features');

        const tracksJson = await tracksRes.json();
        const featuresJson = await featuresRes.json();
        const loadedTracks = tracksJson.data || [];
        setTracks(loadedTracks);
        setFeatures(featuresJson.data || []);

        if (loadedTracks.length > 0) setSelectedTrackId(loadedTracks[0].id);

        if (speakingRes?.ok) {
          const j = await speakingRes.json();
          setSpeakingSummary(j.data || []);
        }

        if (metricsRes?.ok) {
          const j = await metricsRes.json();
          setMetrics(j.data || []);
        }
        
        if (prosodyRes?.ok) {
          const j = await prosodyRes.json();
          setProsody(j.data || []);
        }
        if (graphRes?.ok) {
          const j = await graphRes.json();
          if (j.data) setInteractionGraph(j.data);
        }
        if (annotatedRes?.ok) {
          const j = await annotatedRes.json();
          if (j.data) {
            setAnnotatedVideoStatus(j.data.status || 'not_requested');
            if (j.data.annotated_video_url) setAnnotatedVideoUrl(j.data.annotated_video_url);
          }
        }

        // Check for existing reports for all tracks
        if (loadedTracks.length > 0) {
          const initialStates: Record<string, ReportState> = {};
          for (const track of loadedTracks) {
            initialStates[track.id] = { status: 'idle', report: null, pdf_available: false, error: null, report_id: null };
          }
          // Load existing reports
          await Promise.allSettled(loadedTracks.map(async (track: ParticipantTrack) => {
            try {
              const rRes = await apiClient(`/meetings/${meetingId}/tracks/${track.id}/report`);
              if (rRes.ok) {
                const rJson = await rRes.json();
                if (rJson.data?.status === 'completed' && rJson.data?.report_json) {
                  initialStates[track.id] = {
                    status: 'completed', report: rJson.data.report_json,
                    pdf_available: rJson.data.pdf_available, error: null, report_id: rJson.data.report_id,
                  };
                }
              }
            } catch (_) {}
          }));
          setReportStates(initialStates);
        }
      } catch (err: any) {
        setError(err.message || 'Error loading analysis data');
      } finally {
        setLoading(false);
      }
    };
    if (meetingId) fetchData();
  }, [meetingId]);

  const handleGenerateReport = useCallback(async (trackId: string, forceRegenerate = false) => {
    setReportStates(prev => ({ ...prev, [trackId]: { status: 'generating', report: null, pdf_available: false, error: null, report_id: null } }));
    setActiveTab('report');
    try {
      const url = `/meetings/${meetingId}/tracks/${trackId}/report${forceRegenerate ? '?force_regenerate=true' : ''}`;
      const res = await apiClient(url, { method: 'POST' });
      const json = await res.json();
      if (!res.ok) {
        throw new Error(json.detail || 'Report generation failed');
      }
      const data = json.data;
      setReportStates(prev => ({
        ...prev,
        [trackId]: {
          status: data.status === 'completed' ? 'completed' : 'generating',
          report: data.report_json || null,
          pdf_available: data.pdf_available || false,
          error: null,
          report_id: data.report_id,
        }
      }));
    } catch (e: any) {
      setReportStates(prev => ({
        ...prev,
        [trackId]: { status: 'failed', report: null, pdf_available: false, error: e.message, report_id: null }
      }));
    }
  }, [meetingId]);

  if (loading) return <div className="p-6">Loading analysis...</div>;
  if (error) return <div className="p-6 text-red-500">{error}</div>;
  if (tracks.length === 0) return <div className="p-6">No participants detected for this meeting.</div>;

  const selectedTrack = tracks.find(t => t.id === selectedTrackId);
  const participantFeatures = features.filter(f => f.participant_track_id === selectedTrackId);
  const currentReport = selectedTrackId ? reportStates[selectedTrackId] : null;

  const getSidebarStats = (trackId: string) => {
    const speechData = speakingSummary.find(s => s.track_id === trackId);
    return {
      speechRatio: speechData?.speech_ratio != null ? `${Math.round(speechData.speech_ratio * 100)}%` : '—',
      turns: speechData?.turn_count != null ? `${speechData.turn_count} turns` : '—'
    };
  };

  // Visual Tab Data
  const yawData = participantFeatures
    .filter(f => f.values?.rotation?.yaw !== undefined)
    .map(f => ({ timestamp_ms: f.timestamp_ms, value: f.values.rotation!.yaw }));
  const pitchData = participantFeatures
    .filter(f => f.values?.rotation?.pitch !== undefined)
    .map(f => ({ timestamp_ms: f.timestamp_ms, value: f.values.rotation!.pitch }));
  const rollData = participantFeatures
    .filter(f => f.values?.rotation?.roll !== undefined)
    .map(f => ({ timestamp_ms: f.timestamp_ms, value: f.values.rotation!.roll }));
  const gazeBearingData = participantFeatures
    .filter(f => f.feature_type === 'gaze' && f.values?.gaze?.bearing !== undefined)
    .map(f => ({ timestamp_ms: f.timestamp_ms, value: f.values.gaze!.bearing }));
  const bodyKeypointsData = participantFeatures
    .filter(f => f.feature_type === 'body_pose' && f.values?.keypoints !== undefined)
    .map(f => ({ timestamp_ms: f.timestamp_ms, value: f.values.keypoints!.length }));
  const handsData = participantFeatures
    .filter(f => f.feature_type === 'hand_pose' && f.values?.hands !== undefined)
    .map(f => ({ timestamp_ms: f.timestamp_ms, value: f.values.hands!.length }));

  const emotionFeatures = participantFeatures.filter(f => f.feature_type === 'emotion' && f.values?.emotions);
  let emotionChartData: { name: string; probability: number }[] = [];
  if (emotionFeatures.length > 0) {
    const emotionSums: Record<string, number> = { neutral: 0, happy: 0, sad: 0, angry: 0, surprise: 0, fear: 0 };
    emotionFeatures.forEach(f => {
      Object.entries(f.values.emotions || {}).forEach(([emotion, val]) => {
        if (emotionSums[emotion] !== undefined) emotionSums[emotion] += val;
        else emotionSums[emotion] = val;
      });
    });
    emotionChartData = Object.keys(emotionSums).map(k => ({ name: k, probability: emotionSums[k] / emotionFeatures.length }));
  }

  const selectedSpeech = speakingSummary.find(s => s.track_id === selectedTrackId);

  const speechTabContent = () => {
    if (!speakingSummary || speakingSummary.length === 0)
      return <div className="p-4 bg-gray-50 border rounded text-gray-700">Speech analysis not yet available.</div>;
    return (
      <div className="space-y-6">
        {selectedSpeech ? (
          <div className="flex justify-between border rounded p-4 bg-gray-50 text-center">
            <div><p className="text-sm text-gray-500 font-semibold">Speaking Time</p><p className="text-xl">{selectedSpeech.speaking_time_seconds ? formatTime(selectedSpeech.speaking_time_seconds) : '0m 0s'}</p></div>
            <div><p className="text-sm text-gray-500 font-semibold">Speech Ratio</p><p className="text-xl">{selectedSpeech.speech_ratio ? Math.round(selectedSpeech.speech_ratio * 100) : 0}%</p></div>
            <div><p className="text-sm text-gray-500 font-semibold">Turns</p><p className="text-xl">{selectedSpeech.turn_count || 0}</p></div>
            <div><p className="text-sm text-gray-500 font-semibold">Avg Turn</p><p className="text-xl">{selectedSpeech.avg_turn_duration_seconds ? Number(selectedSpeech.avg_turn_duration_seconds).toFixed(1) + 's' : '0s'}</p></div>
          </div>
        ) : <p className="text-gray-500">No speech data for this participant.</p>}
          <div className="bg-white p-4 border rounded">
            <h3 className="font-semibold mb-2">Prosody & Voice Dynamics</h3>
            <p className="text-sm text-gray-500 mb-4">Pitch (F0) and Energy contours extracted natively via Praat/Parselmouth.</p>
            {(() => {
              const trackProsody = prosody.filter(p => p.participant_track_id === selectedTrackId);
              const trackMetrics = metrics.filter(m => m.participant_track_id === selectedTrackId);
              const medianF0 = trackMetrics.find(m => m.metric_key === 'pitch_p50_hz')?.value;
              const p10F0 = trackMetrics.find(m => m.metric_key === 'pitch_p10_hz')?.value;
              const p90F0 = trackMetrics.find(m => m.metric_key === 'pitch_p90_hz')?.value;
              return <ProsodyChart data={trackProsody} medianF0={medianF0} p10F0={p10F0} p90F0={p90F0} />
            })()}
          </div>
          <div className="bg-white p-4 border rounded">
            <h3 className="font-semibold mb-4">Speaking Ratio Comparison</h3>
          {speakingSummary.map(s => (
            <div key={s.track_id} className="mb-2 flex items-center">
              <div className="w-24 text-sm font-medium">{s.track_label}</div>
              <div className="flex-1 bg-gray-200 h-4 rounded mx-2 overflow-hidden">
                <div className="bg-blue-500 h-full" style={{ width: `${(s.speech_ratio || 0) * 100}%` }}></div>
              </div>
              <div className="w-12 text-sm text-right">{Math.round((s.speech_ratio || 0) * 100)}%</div>
            </div>
          ))}
        </div>
        {selectedSpeech?.turns && selectedSpeech.turns.length > 0 && (
          <div className="bg-white p-4 border rounded">
            <h3 className="font-semibold mb-4 border-b pb-2">Transcript</h3>
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {selectedSpeech.turns.map((turn, i) => (
                <div key={i} className="text-sm">
                  <span className="text-gray-500 font-mono">[{formatTime(turn.start)}]</span> {turn.text}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  const interactionsTabContent = () => {
    if (!interactionGraph || !interactionGraph.nodes || interactionGraph.nodes.length === 0)
      return <div className="p-4 bg-gray-50 border rounded text-gray-700">Interaction analysis not yet available.</div>;
    const sortedEdges = [...(interactionGraph.edges || [])].sort((a, b) => b.exchanges - a.exchanges);
    const pairExchanges: Record<string, number> = {};
    interactionGraph.edges.forEach(e => {
      const pairId = [e.from, e.to].sort().join('-');
      pairExchanges[pairId] = (pairExchanges[pairId] || 0) + e.exchanges;
    });
    const mostActivePairId = Object.entries(pairExchanges).sort((a, b) => b[1] - a[1])[0]?.[0];
    const chartNodes = interactionGraph.nodes.map(n => {
      const track = tracks.find(t => t.id === n.track_id);
      return { label: track?.track_label || n.track_id, speaking_time: n.speaking_time };
    });
    return (
      <div className="space-y-6">
        <div className="bg-white p-4 border rounded">
            <h3 className="font-semibold mb-2">Behavioral Radar</h3>
            <p className="text-sm text-gray-500 mb-4">Multi-modal traits comparing participant dominance and engagement.</p>
            {(() => {
              const radarData = tracks.map(track => {
                const trackMetrics = metrics.filter(m => m.participant_track_id === track.id);
                const getM = (k: string) => trackMetrics.find(m => m.metric_key === k)?.value || 0;
                return {
                  track_label: track.track_label,
                  dominance: getM('multimodal_dominance'),
                  participation: getM('multimodal_participation'),
                  speech_ratio: getM('speech_ratio'),
                  listener_gaze: getM('avg_listener_gaze_on_speaker_pct')
                };
              });
              return <ParticipationRadar data={radarData} />
            })()}
          </div>
          <div className="bg-white p-4 border rounded h-64">
            <h3 className="font-semibold mb-4">Meeting Participation (Speaking Time)</h3>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart layout="vertical" data={chartNodes} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" />
              <YAxis dataKey="label" type="category" width={80} />
              <Tooltip formatter={(val: any) => formatTime(Number(val))} />
              <Bar dataKey="speaking_time" fill="#8884d8" name="Speaking Time" />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="bg-white p-4 border rounded">
          <h3 className="font-semibold mb-4">Interaction Matrix</h3>
          <table className="w-full text-left border-collapse">
            <thead><tr className="border-b"><th className="py-2">From</th><th className="py-2">To</th><th className="py-2 text-center">Exchanges</th><th className="py-2 text-center">Quick Responses</th></tr></thead>
            <tbody>
              {sortedEdges.map((e, i) => {
                const isMostActive = [e.from, e.to].sort().join('-') === mostActivePairId;
                const fromLabel = tracks.find(t => t.id === e.from)?.track_label || e.from;
                const toLabel = tracks.find(t => t.id === e.to)?.track_label || e.to;
                return (
                  <tr key={i} className={`border-b ${isMostActive ? 'bg-yellow-50' : ''}`}>
                    <td className="py-2">{fromLabel}</td><td className="py-2">{toLabel}</td>
                    <td className="py-2 text-center">{e.exchanges}</td><td className="py-2 text-center">{e.quick_responses}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  const reportTabContent = () => {
    if (!currentReport) return <div className="p-4 text-gray-500">Select a participant to generate their report.</div>;
    if (currentReport.status === 'generating') {
      return (
        <div className="flex flex-col items-center justify-center py-16 space-y-4">
          <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-blue-700 font-medium">Generating visual report...</p>
          <p className="text-sm text-gray-500">Aggregating visual data and calling LLM. This may take 30–90 seconds.</p>
        </div>
      );
    }
    if (currentReport.status === 'failed') {
      return (
        <div className="p-4 bg-red-50 border border-red-200 rounded">
          <p className="text-red-700 font-medium">Report generation failed. Existing visual analysis is still available.</p>
          <p className="text-sm text-red-500 mt-1">{currentReport.error}</p>
          <button onClick={() => selectedTrackId && handleGenerateReport(selectedTrackId)}
            className="mt-3 px-4 py-2 bg-red-600 text-white rounded text-sm hover:bg-red-700">
            Retry
          </button>
        </div>
      );
    }
    if (currentReport.status === 'completed' && currentReport.report) {
      return (
        <ReportPanel
          report={currentReport.report}
          meetingId={meetingId!}
          trackId={selectedTrackId!}
          pdfAvailable={currentReport.pdf_available}
          onRegenerate={() => selectedTrackId && handleGenerateReport(selectedTrackId, true)}
        />
      );
    }
    return (
      <div className="p-6 bg-gray-50 border rounded text-center">
        <p className="text-gray-600 mb-3">No report generated yet for <b>{selectedTrack?.track_label}</b>.</p>
        <p className="text-sm text-gray-500 mb-4">The report uses existing visual analysis data (head, gaze, posture, hands, affect). No CV re-inference is performed.</p>
        <button onClick={() => selectedTrackId && handleGenerateReport(selectedTrackId)}
          className="px-5 py-2.5 bg-blue-600 text-white rounded font-semibold hover:bg-blue-700">
          Generate Visual Report
        </button>
      </div>
    );
  };

  return (
    <div className="p-6 max-w-7xl mx-auto flex flex-col md:flex-row gap-6">
      {/* Sidebar */}
      <div className="w-full md:w-1/4">
        <div className="flex items-center space-x-4 mb-6">
          <Link to={-1 as any} className="text-blue-600 hover:underline">&larr; Back</Link>
          <h2 className="text-xl font-bold">Meeting Analysis</h2>
        </div>
        <h3 className="font-semibold text-gray-700 mb-2">Participants</h3>
        <div className="flex flex-col space-y-2">
          {tracks.map(t => {
            const stats = getSidebarStats(t.id);
            const rState = reportStates[t.id];
            const hasReport = rState?.status === 'completed';
            const isGenerating = rState?.status === 'generating';
            return (
              <div key={t.id}
                className={`p-3 rounded-md border text-left flex flex-col cursor-pointer ${selectedTrackId === t.id ? 'bg-blue-50 border-blue-400' : 'bg-white hover:bg-gray-50'}`}
                onClick={() => setSelectedTrackId(t.id)}
              >
                <div className="flex justify-between items-center mb-1">
                  <span className="font-semibold">{t.track_label}</span>
                  <span className="text-xs font-medium text-blue-600">{stats.speechRatio} | {stats.turns}</span>
                </div>
                <div className="text-xs text-gray-500 flex justify-between mb-2">
                  <span>Frames: {t.detection_frame_count}</span>
                  <span>Conf: {t.avg_detection_confidence ? (t.avg_detection_confidence * 100).toFixed(0) + '%' : '—'}</span>
                </div>
                {/* Report button */}
                {isGenerating ? (
                  <span className="text-xs text-blue-600 italic flex items-center gap-1">
                    <span className="inline-block w-3 h-3 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                    Generating report...
                  </span>
                ) : hasReport ? (
                  <div className="flex gap-1">
                    <button
                      onClick={(e) => { e.stopPropagation(); setSelectedTrackId(t.id); setActiveTab('report'); }}
                      className="flex-1 text-xs bg-blue-600 text-white rounded px-2 py-1 hover:bg-blue-700">
                      View Report
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={(e) => { e.stopPropagation(); setSelectedTrackId(t.id); handleGenerateReport(t.id); }}
                    className="text-xs bg-gray-100 border border-gray-300 text-gray-700 rounded px-2 py-1 hover:bg-gray-200 text-left">
                    + Generate Report
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Main content */}
      <div className="w-full md:w-3/4">
        <div className="flex border-b mb-6 flex-wrap">
          {(['visual', 'speech', 'interaction', 'report', 'annotated'] as const).map(tab => (
            <button key={tab}
              className={`px-4 py-2 font-medium capitalize ${activeTab === tab ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
              onClick={() => setActiveTab(tab)}>
              {tab === 'report'
                ? `NTS Report${currentReport?.status === 'completed' ? ' ✓' : currentReport?.status === 'generating' ? ' …' : ''}`
                : tab === 'speech' ? 'Speech & Language'
                : tab === 'interaction' ? 'Interactions'
                : tab === 'annotated'
                  ? `Annotated Video${annotatedVideoStatus === 'completed' ? ' ✓' : ['queued', 'running'].includes(annotatedVideoStatus) ? ' …' : ''}`
                : 'Visual Features'}
            </button>
          ))}
        </div>

        {activeTab === 'visual' && (
          <div className="space-y-8">
            {participantFeatures.length < 5 ? (
              <div className="p-6 bg-yellow-50 text-yellow-800 rounded-md border border-yellow-200">
                Insufficient visual data for {selectedTrack?.track_label}. Needs at least 5 frames of detections.
              </div>
            ) : (
              <>
                {yawData.length > 0 && <FeatureChart data={yawData} metricName="Head Yaw (rad)" />}
                {pitchData.length > 0 && <FeatureChart data={pitchData} metricName="Head Pitch (rad)" />}
                {rollData.length > 0 && <FeatureChart data={rollData} metricName="Head Roll (rad)" />}
                {gazeBearingData.length > 0 && <FeatureChart data={gazeBearingData} metricName="Gaze Bearing" />}
                {bodyKeypointsData.length > 0 && <FeatureChart data={bodyKeypointsData} metricName="Body Keypoints Detected" />}
                {handsData.length > 0 && <FeatureChart data={handsData} metricName="Hands Visible" />}
                {emotionChartData.length > 0 && (
                  <div className="bg-white p-4 border rounded h-64">
                    <h3 className="font-semibold mb-4 text-lg">Facial Affect Distribution</h3>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={emotionChartData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="name" />
                        <YAxis domain={[0, 1]} />
                        <Tooltip formatter={(value: any) => Number(value).toFixed(3)} />
                        <Bar dataKey="probability" fill="#82ca9d" name="Avg Probability" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {activeTab === 'speech' && speechTabContent()}
        {activeTab === 'interaction' && interactionsTabContent()}
        {activeTab === 'report' && reportTabContent()}

        {activeTab === 'annotated' && (
          <div className="space-y-4">
            {annotatedVideoStatus === 'not_requested' && (
              <div className="p-6 bg-gray-50 border rounded text-center">
                <div className="text-4xl mb-3">🎬</div>
                <p className="text-gray-700 font-medium mb-2">No Annotated Video Generated</p>
                <p className="text-sm text-gray-500 mb-4">
                  To generate an annotated video, start a new analysis with the
                  <strong> "Generate Annotated Video"</strong> checkbox enabled in the analyze dialog.
                  The video will show bounding boxes, posture skeletons, and emotion tags for each participant.
                </p>
                <p className="text-xs text-gray-400">
                  Note: This runs as a background job after CV extraction completes and may take several minutes.
                </p>
              </div>
            )}

            {(annotatedVideoStatus === 'queued' || annotatedVideoStatus === 'running') && (
              <div className="flex flex-col items-center justify-center py-16 space-y-4">
                <div className="w-10 h-10 border-4 border-purple-500 border-t-transparent rounded-full animate-spin" />
                <p className="text-purple-700 font-medium">
                  {annotatedVideoStatus === 'queued' ? 'Annotated video queued…' : 'Rendering annotated video…'}
                </p>
                <p className="text-sm text-gray-500">
                  This may take several minutes depending on video length. The page will update automatically.
                </p>
              </div>
            )}

            {annotatedVideoStatus === 'failed' && (
              <div className="p-4 bg-red-50 border border-red-200 rounded">
                <p className="text-red-700 font-medium">Annotated video generation failed.</p>
                {annotatedVideoError && <p className="text-sm text-red-500 mt-1">{annotatedVideoError}</p>}
                <p className="text-sm text-gray-500 mt-2">
                  Re-run the analysis with the "Generate Annotated Video" option to try again.
                </p>
              </div>
            )}

            {(annotatedVideoStatus === 'completed' || annotatedVideoStatus === 'succeeded') && annotatedVideoUrl && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-gray-800">Annotated Meeting Video</h3>
                  <div className="flex items-center gap-3">
                    <span className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded-full font-medium">✓ Ready</span>
                    <a
                      href={annotatedVideoUrl}
                      download
                      className="text-xs bg-purple-600 text-white px-3 py-1.5 rounded hover:bg-purple-700 font-semibold"
                    >
                      ⬇ Download
                    </a>
                  </div>
                </div>
                <div className="bg-black rounded-lg overflow-hidden">
                  <video
                    key={annotatedVideoUrl}
                    controls
                    className="w-full max-h-[540px]"
                    src={annotatedVideoUrl}
                  >
                    Your browser does not support the video tag.
                  </video>
                </div>
                <div className="bg-gray-50 border rounded p-3">
                  <p className="text-xs font-semibold text-gray-500 mb-1">OVERLAYS IN THIS VIDEO</p>
                  <ul className="text-xs text-gray-600 space-y-1">
                    <li>• <strong>Colored bounding boxes</strong> — each participant is assigned a unique color</li>
                    <li>• <strong>Posture skeleton</strong> — 33 body keypoints connected via BlazePose connections</li>
                    <li>• <strong>Head rotation</strong> — Yaw / Pitch / Roll values shown in real-time</li>
                    <li>• <strong>Dominant emotion</strong> — facial affect classification per participant</li>
                    <li>• <strong>Hand visibility</strong> — count of detected hands per frame</li>
                  </ul>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
