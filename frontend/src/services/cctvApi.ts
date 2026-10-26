import axios from 'axios';
import type {
  AuditLog,
  CameraId,
  DepartmentCode,
  ExportStatus,
  LiveTelemetrySnapshot,
  Recommendation,
  ScorecardSuite,
  SessionStatus,
  SpatialZone,
  SystemHealth
} from '../features/cctv/types';

// Default to /cctv-api which is proxied via Vite to CCTV backend (port 8001),
// or override via VITE_CCTV_API_URL.
const API_BASE_URL = import.meta.env.VITE_CCTV_API_URL || '/cctv-api';

export const cctvAxiosClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 8000,
  headers: {
    'Content-Type': 'application/json'
  }
});

export const cctvApi = {
  // Health
  async getHealth(): Promise<SystemHealth | null> {
    try {
      const resp = await cctvAxiosClient.get<SystemHealth>('/health');
      return resp.data;
    } catch (err) {
      console.warn('CCTV backend /health unreachable:', err);
      return null;
    }
  },

  // Session & Streaming
  async getSessionStatus(cameraId: CameraId = 'CAM-01'): Promise<SessionStatus | null> {
    try {
      const resp = await cctvAxiosClient.get<SessionStatus>(`/api/v1/sessions/status/${cameraId}`);
      return resp.data;
    } catch (err) {
      console.warn(`Error fetching status for ${cameraId}:`, err);
      return null;
    }
  },

  async startSession(cameraId: CameraId = 'CAM-01'): Promise<any> {
    const resp = await cctvAxiosClient.post(`/api/v1/sessions/start?camera_id=${cameraId}`);
    return resp.data;
  },

  async stopSession(cameraId: CameraId = 'CAM-01'): Promise<any> {
    const resp = await cctvAxiosClient.post(`/api/v1/sessions/stop?camera_id=${cameraId}`);
    return resp.data;
  },

  getStreamUrl(cameraId: CameraId = 'CAM-01'): string {
    return `${API_BASE_URL}/api/v1/stream/live/${cameraId}`;
  },

  async uploadVideo(file: File, cameraId: CameraId = 'CAM-01'): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    const resp = await cctvAxiosClient.post(`/api/v1/videos/upload?camera_id=${cameraId}`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 120000
    });
    return resp.data;
  },

  // Live Telemetry
  async getLiveTelemetry(cameraId: CameraId = 'CAM-01'): Promise<LiveTelemetrySnapshot | null> {
    try {
      const resp = await cctvAxiosClient.get<LiveTelemetrySnapshot>(`/api/v1/telemetry/live/${cameraId}`);
      return resp.data;
    } catch (err) {
      console.warn(`Error fetching telemetry for ${cameraId}:`, err);
      return null;
    }
  },

  // Zones
  async getZones(cameraId?: CameraId): Promise<SpatialZone[]> {
    try {
      const url = cameraId ? `/api/v1/zones?camera_id=${cameraId}` : '/api/v1/zones';
      const resp = await cctvAxiosClient.get<SpatialZone[]>(url);
      return resp.data || [];
    } catch (err) {
      console.warn('Error fetching zones:', err);
      return [];
    }
  },

  async createZone(zonePayload: Partial<SpatialZone>): Promise<SpatialZone | null> {
    try {
      const resp = await cctvAxiosClient.post<SpatialZone>('/api/v1/zones', zonePayload);
      return resp.data;
    } catch (err) {
      console.error('Error creating zone:', err);
      throw err;
    }
  },

  async deleteZone(zoneId: string, cameraId: CameraId = 'CAM-01'): Promise<boolean> {
    try {
      const resp = await cctvAxiosClient.delete(`/api/v1/zones/${zoneId}?camera_id=${cameraId}`);
      return resp.status === 200;
    } catch (err) {
      console.error(`Error deleting zone ${zoneId}:`, err);
      return false;
    }
  },

  // Scorecards & Recommendations
  async getScorecards(cameraId: CameraId = 'CAM-01', department: DepartmentCode = 'ENG'): Promise<ScorecardSuite | null> {
    try {
      const resp = await cctvAxiosClient.get<ScorecardSuite>(
        `/api/v1/analytics/scorecards?camera_id=${cameraId}&department=${department}`
      );
      return resp.data;
    } catch (err) {
      console.warn('Error fetching scorecards:', err);
      return null;
    }
  },

  async getRecommendations(cameraId: CameraId = 'CAM-01'): Promise<Recommendation[]> {
    try {
      const resp = await cctvAxiosClient.get<Recommendation[]>(`/api/v1/analytics/recommendations?camera_id=${cameraId}`);
      return resp.data || [];
    } catch (err) {
      console.warn('Error fetching recommendations:', err);
      return [];
    }
  },

  async ingestOperationalOutcomes(payload: any): Promise<any> {
    const resp = await cctvAxiosClient.post('/api/v1/ingest/operational-outcomes', payload);
    return resp.data;
  },

  // Video Export
  async triggerVideoExport(cameraId: CameraId = 'CAM-01', maxFrames: number = 150): Promise<{ job_id: string; status: string; output_filename: string } | null> {
    try {
      const resp = await cctvAxiosClient.post(`/api/v1/export/video?camera_id=${cameraId}&max_frames=${maxFrames}`);
      return resp.data;
    } catch (err) {
      console.error('Error triggering video export:', err);
      return null;
    }
  },

  async getExportStatus(jobId: string): Promise<ExportStatus | null> {
    try {
      const resp = await cctvAxiosClient.get<ExportStatus>(`/api/v1/export/status/${jobId}`);
      return resp.data;
    } catch (err) {
      console.warn(`Error polling export status for ${jobId}:`, err);
      return null;
    }
  },

  // Audit Logs
  async getAuditLogs(limit: number = 50): Promise<AuditLog[]> {
    try {
      const resp = await cctvAxiosClient.get<AuditLog[]>(`/api/v1/system/audit-logs?limit=${limit}`);
      return resp.data || [];
    } catch (err) {
      console.warn('Error fetching audit logs:', err);
      return [];
    }
  }
};

export const apiService = cctvApi;
