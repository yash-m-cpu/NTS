import React, { createContext, useContext, useEffect, useState } from 'react';
import type { CameraId, DepartmentCode, SystemHealth } from '../types';
import { cctvApi } from '../../../services/cctvApi';

interface AppContextType {
  selectedCamera: CameraId;
  setSelectedCamera: (cam: CameraId) => void;
  selectedDepartment: DepartmentCode;
  setSelectedDepartment: (dept: DepartmentCode) => void;
  health: SystemHealth | null;
  refreshHealth: () => Promise<void>;
  activeAnalyzedVideo: string | null;
  setActiveAnalyzedVideo: (name: string | null) => void;
  isUploadModalOpen: boolean;
  setIsUploadModalOpen: (open: boolean) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [selectedCamera, setSelectedCamera] = useState<CameraId>('CAM-01');
  const [selectedDepartment, setSelectedDepartment] = useState<DepartmentCode>('ENG');
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [activeAnalyzedVideo, setActiveAnalyzedVideo] = useState<string | null>(null);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState<boolean>(false);

  const refreshHealth = async () => {
    try {
      const res = await cctvApi.getHealth();
      setHealth(res);
    } catch (_) {
      setHealth(null);
    }
  };

  useEffect(() => {
    refreshHealth();
    const interval = setInterval(refreshHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <AppContext.Provider
      value={{
        selectedCamera,
        setSelectedCamera,
        selectedDepartment,
        setSelectedDepartment,
        health,
        refreshHealth,
        activeAnalyzedVideo,
        setActiveAnalyzedVideo,
        isUploadModalOpen,
        setIsUploadModalOpen
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = (): AppContextType => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};
