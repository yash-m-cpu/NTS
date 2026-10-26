import { Navigate, Outlet, Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../state/authStore';
import OrgSwitcher from '../components/OrgSwitcher';
import { apiClient } from '../lib/apiClient';
import { ArrowLeft, Video } from 'lucide-react';

export default function ProtectedLayout() {
  const { accessToken, clearAuth } = useAuthStore();
  const navigate = useNavigate();

  if (!accessToken) {
    return <Navigate to="/login" replace />;
  }

  const handleLogout = async () => {
    await apiClient('/auth/logout', { method: 'POST' });
    clearAuth();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white shadow-xs border-b border-gray-200 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            <div className="flex items-center space-x-6">
              <Link
                to="/"
                className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-600 hover:text-blue-600 bg-gray-100 hover:bg-blue-50 px-2.5 py-1.5 rounded-lg border border-gray-200 transition-colors"
                title="Return to Platform Home"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Platform Home</span>
              </Link>

              <div className="h-6 w-px bg-gray-200 hidden sm:block" />

              <h1 className="text-xl font-bold text-blue-600 tracking-tight">NTS Platform</h1>
              <nav className="flex items-center space-x-2">
                <Link to="/dashboard" className="text-gray-700 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium">Dashboard</Link>
                <Link
                  to="/cctv"
                  className="inline-flex items-center gap-1.5 text-gray-600 hover:text-blue-600 bg-gray-50 hover:bg-gray-100 px-3 py-1.5 rounded-lg border border-gray-200 text-xs font-semibold transition-colors"
                  title="Switch to CCTV Workplace Analytics"
                >
                  <Video className="w-3.5 h-3.5 text-blue-600" />
                  <span>CCTV Analytics →</span>
                </Link>
              </nav>
            </div>
            <div className="flex items-center space-x-4">
              <OrgSwitcher />
              <button 
                onClick={handleLogout}
                className="text-sm text-red-600 hover:text-red-800 font-medium px-3 py-2 cursor-pointer"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
    </div>
  );
}
