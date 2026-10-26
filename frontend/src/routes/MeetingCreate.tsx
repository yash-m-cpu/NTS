import React, { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { apiClient } from '../lib/apiClient';

export default function MeetingCreate() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();

  const [title, setTitle] = useState('');
  const [sourceType, setSourceType] = useState('upload');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title || !projectId) return;

    setLoading(true);
    setError('');

    try {
      const res = await apiClient('/meetings', {
        method: 'POST',
        body: JSON.stringify({
          project_id: projectId,
          title,
          source_type: sourceType,
        }),
      });

      if (!res.ok) {
        throw new Error('Failed to create meeting');
      }

      await res.json();
      
      // Navigate to the meeting detail or project detail (here we just go back to project detail)
      // or to the upload page? We can just navigate to project detail for now.
      navigate(`/projects/${projectId}`);
    } catch (err: any) {
      setError(err.message || 'Error creating meeting');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-lg mx-auto">
      <h2 className="text-2xl font-bold mb-4">Create Meeting</h2>
      
      {error && <div className="text-red-500 mb-4">{error}</div>}
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block mb-1 font-medium">Title</label>
          <input
            type="text"
            className="w-full border p-2 rounded"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />
        </div>
        
        <div>
          <label className="block mb-1 font-medium">Source Type</label>
          <select
            className="w-full border p-2 rounded"
            value={sourceType}
            onChange={(e) => setSourceType(e.target.value)}
          >
            <option value="upload">Upload</option>
            <option value="live_camera">Live Camera</option>
          </select>
        </div>
        
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => navigate(`/projects/${projectId}`)}
            className="bg-gray-300 px-4 py-2 rounded"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading || !title}
            className="bg-blue-600 text-white px-4 py-2 rounded disabled:bg-blue-300"
          >
            {loading ? 'Creating...' : 'Create'}
          </button>
        </div>
      </form>
    </div>
  );
}
