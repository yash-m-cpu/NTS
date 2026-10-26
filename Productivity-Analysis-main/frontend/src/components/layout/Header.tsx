import React from 'react';
import { Camera, RefreshCw, Upload, Building } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { CovenantBadge } from '../common/CovenantBadge';
import type { CameraId, DepartmentCode } from '../../types';

export const Header: React.FC = () => {
  const {
    selectedCamera,
    setSelectedCamera,
    selectedDepartment,
    setSelectedDepartment,
    health,
    refreshHealth,
    setIsUploadModalOpen,
    activeAnalyzedVideo
  } = useApp();

  return (
    <header className="sticky top-0 z-30 w-full bg-slate-950/80 backdrop-blur-md border-b border-slate-800 px-6 py-3 flex flex-wrap items-center justify-between gap-4">
      {/* Brand & Covenant Badge */}
      <div className="flex items-center gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-lg font-bold text-slate-100 tracking-tight">
              WBPIS Intelligence
            </h1>
            <CovenantBadge />
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Workplace Productivity & Workflow Intelligence System | Spatial Ergonomics & Bottlenecks
          </p>
        </div>
      </div>

      {/* Selectors & Actions */}
      <div className="flex items-center flex-wrap gap-3">
        {/* Active video indicator if set */}
        {activeAnalyzedVideo && (
          <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-sky-950/60 border border-sky-500/30 text-sky-300 text-xs">
            <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-pulse" />
            <span className="font-mono truncate max-w-[140px]">{activeAnalyzedVideo}</span>
          </div>
        )}

        {/* Backend Health Pill */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-900 border border-slate-800 text-xs">
          {health?.status === 'HEALTHY' ? (
            <>
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              <span className="text-emerald-300 font-medium">Backend Online (v{health.version})</span>
            </>
          ) : (
            <>
              <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
              <span className="text-amber-300 font-medium">Backend Standby</span>
            </>
          )}
          <button
            onClick={refreshHealth}
            title="Refresh backend status"
            className="text-slate-400 hover:text-slate-200 ml-1 transition-colors"
          >
            <RefreshCw className="w-3 h-3" />
          </button>
        </div>

        {/* Camera Selector */}
        <div className="flex items-center gap-1.5 bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1 text-xs">
          <Camera className="w-3.5 h-3.5 text-slate-400 shrink-0" />
          <label htmlFor="cam-select" className="text-slate-400">Stream:</label>
          <select
            id="cam-select"
            value={selectedCamera}
            onChange={(e) => setSelectedCamera(e.target.value as CameraId)}
            className="bg-transparent text-slate-200 font-medium focus:outline-none cursor-pointer"
          >
            <option value="CAM-01" className="bg-slate-900 text-slate-200">CAM-01</option>
            <option value="CAM-02" className="bg-slate-900 text-slate-200">CAM-02</option>
            <option value="CAM-03" className="bg-slate-900 text-slate-200">CAM-03</option>
          </select>
        </div>

        {/* Department Selector */}
        <div className="flex items-center gap-1.5 bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1 text-xs">
          <Building className="w-3.5 h-3.5 text-slate-400 shrink-0" />
          <label htmlFor="dept-select" className="text-slate-400">Dept:</label>
          <select
            id="dept-select"
            value={selectedDepartment}
            onChange={(e) => setSelectedDepartment(e.target.value as DepartmentCode)}
            className="bg-transparent text-slate-200 font-medium focus:outline-none cursor-pointer"
          >
            <option value="ENG" className="bg-slate-900 text-slate-200">ENG</option>
            <option value="PRODUCT" className="bg-slate-900 text-slate-200">PRODUCT</option>
            <option value="OPERATIONS" className="bg-slate-900 text-slate-200">OPERATIONS</option>
            <option value="SALES" className="bg-slate-900 text-slate-200">SALES</option>
          </select>
        </div>

        {/* Upload Custom Video Button */}
        <button
          onClick={() => setIsUploadModalOpen(true)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold rounded-lg shadow-sm transition-colors"
        >
          <Upload className="w-3.5 h-3.5" />
          <span>Upload Video</span>
        </button>
      </div>
    </header>
  );
};
