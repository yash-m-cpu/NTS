import React from 'react';
import { Outlet } from 'react-router-dom';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { VideoUploadModal } from '../video/VideoUploadModal';
import { ErrorBoundary } from '../common/ErrorBoundary';

export const Layout: React.FC = () => {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Header />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto p-6 md:p-8 bg-slate-900/40">
          <div className="max-w-7xl mx-auto space-y-6">
            <ErrorBoundary fallbackTitle="View Rendering Error">
              <Outlet />
            </ErrorBoundary>
          </div>
        </main>
      </div>
      <VideoUploadModal />
    </div>
  );
};
