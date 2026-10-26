import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiClient } from '../lib/apiClient';
import { useAuthStore } from '../state/authStore';

export default function Dashboard() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const { user } = useAuthStore();

  const loadData = async () => {
    try {
      setLoading(true);
      const res = await apiClient('/projects');
      if (res.ok) {
        const data = await res.json();
        setProjects(data.data || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateProject = async () => {
    const name = window.prompt("Enter new project name:");
    if (!name) return;
    
    try {
      const res = await apiClient('/projects', {
        method: 'POST',
        body: JSON.stringify({ name, description: "A new NTS analysis project" })
      });
      if (res.ok) {
        // Reload projects inline without full page refresh
        await loadData();
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Welcome, {user?.full_name || 'User'}</h1>
        <button 
          onClick={handleCreateProject}
          className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md cursor-pointer transition-colors"
        >
          New Project
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider">Total Projects</h3>
          <p className="mt-2 text-3xl font-semibold text-gray-900">{projects.length}</p>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider">Total Meetings</h3>
          <p className="mt-2 text-3xl font-semibold text-gray-900">-</p>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider">Avg NTS Score</h3>
          <p className="mt-2 text-3xl font-semibold text-gray-900">-</p>
        </div>
      </div>

      <div className="bg-white shadow-sm rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-6 py-5 border-b border-gray-200">
          <h3 className="text-lg font-medium leading-6 text-gray-900">Your Projects</h3>
        </div>
        {loading ? (
          <div className="p-6 text-center text-gray-500">Loading projects...</div>
        ) : projects.length > 0 ? (
          <ul className="divide-y divide-gray-200">
            {projects.map((p: any) => (
              <li key={p.id}>
                <div className="flex items-center justify-between hover:bg-gray-50 px-6 py-4 transition-colors">
                  <Link to={`/projects/${p.id}`} className="block flex-1">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium text-blue-600 truncate">{p.name}</p>
                      <div className="ml-2 flex-shrink-0 flex">
                        <p className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                          Active
                        </p>
                      </div>
                    </div>
                  </Link>
                  <button 
                    onClick={async (e) => {
                      e.preventDefault();
                      if (window.confirm("Are you sure you want to delete this project?")) {
                        await apiClient(`/projects/${p.id}`, { method: 'DELETE' });
                        await loadData();
                      }
                    }}
                    className="ml-4 text-red-600 hover:text-red-800 text-sm font-medium px-3 py-1 border border-red-200 rounded hover:bg-red-50"
                  >
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <div className="p-12 text-center">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
              <path vectorEffect="non-scaling-stroke" strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 13h6m-3-3v6m-9 1V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-gray-900">No projects</h3>
            <p className="mt-1 text-sm text-gray-500">Get started by creating a new project to analyze meetings.</p>
          </div>
        )}
      </div>
    </div>
  );
}
