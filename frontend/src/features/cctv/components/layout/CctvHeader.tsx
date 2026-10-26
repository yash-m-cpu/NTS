import React from 'react';
import { Camera, RefreshCw, Upload, Building, ArrowLeft, Layers } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useApp } from '../../context/AppContext';
import { CovenantBadge } from '../common/CovenantBadge';
import type { CameraId, DepartmentCode } from '../../types';

export const CctvHeader: React.FC = () => {
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
    <header className="sticky top-0 z-30 w-full bg-white/95 backdrop-blur-md border-b border-gray-200 px-6 py-3 flex flex-wrap items-center justify-between gap-4 shadow-xs">
      {/* Brand & Covenant Badge */}
      <div className="flex items-center gap-4">
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-600 hover:text-blue-600 bg-gray-100 hover:bg-blue-50 px-2.5 py-1.5 rounded-lg border border-gray-200 transition-colors"
          title="Return to Platform Home"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Platform Home</span>
        </Link>

        <div className="h-6 w-px bg-gray-200" />

        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-base font-bold text-gray-900 tracking-tight flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-blue-600" />
              CCTV Workplace Analytics
            </h1>
            <CovenantBadge />
          </div>
          <p className="text-xs text-gray-500 mt-0.5">
            Space Utilization, Activity Classification & Workflow Bottlenecks
          </p>
        </div>
      </div>

      {/* Selectors & Actions */}
      <div className="flex items-center flex-wrap gap-3">
        {/* Active video indicator if set */}
        {activeAnalyzedVideo && (
          <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-blue-50 border border-blue-200 text-blue-700 text-xs">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
            <span className="font-mono truncate max-w-[140px]">{activeAnalyzedVideo}</span>
          </div>
        )}

        {/* Backend Health Pill */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-gray-50 border border-gray-200 text-xs">
          {health?.status === 'HEALTHY' ? (
            <>
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              <span className="text-emerald-700 font-medium">CCTV API Online (v{health.version})</span>
            </>
          ) : (
            <>
              <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
              <span className="text-amber-700 font-medium">CCTV API Standby</span>
            </>
          )}
          <button
            onClick={refreshHealth}
            title="Refresh backend status"
            className="text-gray-400 hover:text-gray-700 ml-1 transition-colors"
          >
            <RefreshCw className="w-3 h-3" />
          </button>
        </div>

        {/* Camera Selector */}
        <div className="flex items-center gap-1.5 bg-gray-50 border border-gray-200 rounded-lg px-2.5 py-1 text-xs">
          <Camera className="w-3.5 h-3.5 text-gray-500 shrink-0" />
          <label htmlFor="cam-select" className="text-gray-500">Stream:</label>
          <select
            id="cam-select"
            value={selectedCamera}
            onChange={(e) => setSelectedCamera(e.target.value as CameraId)}
            className="bg-transparent text-gray-800 font-medium focus:outline-none cursor-pointer"
          >
            <option value="CAM-01">CAM-01</option>
            <option value="CAM-02">CAM-02</option>
            <option value="CAM-03">CAM-03</option>
          </select>
        </div>

        {/* Department Selector */}
        <div className="flex items-center gap-1.5 bg-gray-50 border border-gray-200 rounded-lg px-2.5 py-1 text-xs">
          <Building className="w-3.5 h-3.5 text-gray-500 shrink-0" />
          <label htmlFor="dept-select" className="text-gray-500">Dept:</label>
          <select
            id="dept-select"
            value={selectedDepartment}
            onChange={(e) => setSelectedDepartment(e.target.value as DepartmentCode)}
            className="bg-transparent text-gray-800 font-medium focus:outline-none cursor-pointer"
          >
            <option value="ENG">ENG</option>
            <option value="PRODUCT">PRODUCT</option>
            <option value="OPERATIONS">OPERATIONS</option>
            <option value="SALES">SALES</option>
          </select>
        </div>

        {/* Upload Custom Video Button */}
        <button
          onClick={() => setIsUploadModalOpen(true)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-xs transition-colors cursor-pointer"
        >
          <Upload className="w-3.5 h-3.5" />
          <span>Upload Video</span>
        </button>

        {/* Switch to Skill Analysis */}
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-semibold rounded-lg border border-gray-200 transition-colors"
          title="Switch to Skill Analysis Platform"
        >
          <span>Skill Analysis →</span>
        </Link>
      </div>
    </header>
  );
};
