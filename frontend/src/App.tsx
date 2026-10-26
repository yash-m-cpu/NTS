import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { LandingPage } from './routes/LandingPage';
import Login from './routes/Login';
import Register from './routes/Register';
import ProtectedLayout from './routes/ProtectedLayout';
import Dashboard from './routes/Dashboard';
import ProjectDetail from './routes/ProjectDetail';
import MeetingCreate from './routes/MeetingCreate';
import MeetingAnalysis from './routes/MeetingAnalysis';

// CCTV Feature Layout & Pages
import { CctvLayout } from './features/cctv/components/layout/CctvLayout';
import {
  View01LiveCctv,
  View02TrackDetails,
  View03WorkflowEfficiency,
  View04ActivityDistribution,
  View05OccupancyPresence,
  View06OutputEffectiveness,
  View07TeamWorkspace,
  View08HistoricalComparison,
  View09VideoExport,
  View10DataQuality,
  ZoneEditor
} from './features/cctv/pages';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Universal Landing Page */}
        <Route path="/" element={<LandingPage />} />

        {/* Public Skill Analysis Auth Routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* Skill Analysis Feature Branch (Protected) */}
        <Route element={<ProtectedLayout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/projects/:projectId" element={<ProjectDetail />} />
          <Route path="/projects/:projectId/meetings/new" element={<MeetingCreate />} />
          <Route path="/meetings/:meetingId/analysis" element={<MeetingAnalysis />} />
        </Route>

        {/* CCTV Workplace Analytics Feature Branch */}
        <Route path="/cctv" element={<CctvLayout />}>
          <Route index element={<View01LiveCctv />} />
          <Route path="view02" element={<View02TrackDetails />} />
          <Route path="view03" element={<View03WorkflowEfficiency />} />
          <Route path="view04" element={<View04ActivityDistribution />} />
          <Route path="view05" element={<View05OccupancyPresence />} />
          <Route path="view06" element={<View06OutputEffectiveness />} />
          <Route path="view07" element={<View07TeamWorkspace />} />
          <Route path="view08" element={<View08HistoricalComparison />} />
          <Route path="view09" element={<View09VideoExport />} />
          <Route path="view10" element={<View10DataQuality />} />
          <Route path="zones" element={<ZoneEditor />} />
        </Route>

        {/* Fallback to Platform Landing */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
