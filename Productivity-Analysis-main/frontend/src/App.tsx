import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppProvider } from './context/AppContext';
import { Layout } from './components/layout/Layout';
import { View01LiveCctv } from './pages/View01LiveCctv';
import { View02TrackDetails } from './pages/View02TrackDetails';
import { View03WorkflowEfficiency } from './pages/View03WorkflowEfficiency';
import { View04ActivityDistribution } from './pages/View04ActivityDistribution';
import { View05OccupancyPresence } from './pages/View05OccupancyPresence';
import { View06OutputEffectiveness } from './pages/View06OutputEffectiveness';
import { View07TeamWorkspace } from './pages/View07TeamWorkspace';
import { View08HistoricalComparison } from './pages/View08HistoricalComparison';
import { View09VideoExport } from './pages/View09VideoExport';
import { View10DataQuality } from './pages/View10DataQuality';
import { ZoneEditor } from './pages/ZoneEditor';

export const App: React.FC = () => {
  return (
    <AppProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
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
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AppProvider>
  );
};

export default App;
