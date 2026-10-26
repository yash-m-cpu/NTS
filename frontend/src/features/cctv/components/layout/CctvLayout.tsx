import React from 'react';
import { Outlet } from 'react-router-dom';
import { AppProvider } from '../../context/AppContext';
import { CctvHeader } from './CctvHeader';
import { CctvSidebar } from './CctvSidebar';
import { VideoUploadModal } from '../video/VideoUploadModal';
import { ErrorBoundary } from '../common/ErrorBoundary';

export const CctvLayout: React.FC = () => {
  return (
    <AppProvider>
      <div className="min-h-screen bg-gray-50 text-gray-900 flex flex-col font-sans">
        <CctvHeader />
        <div className="flex flex-1 overflow-hidden">
          <CctvSidebar />
          <main className="flex-1 overflow-y-auto p-6 md:p-8 bg-gray-50/50">
            <div className="max-w-7xl mx-auto space-y-6">
              <ErrorBoundary fallbackTitle="CCTV Analytics View Error">
                <Outlet />
              </ErrorBoundary>
            </div>
          </main>
        </div>
        <VideoUploadModal />
      </div>
    </AppProvider>
  );
};
