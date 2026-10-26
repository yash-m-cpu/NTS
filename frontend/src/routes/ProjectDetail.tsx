import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '../lib/apiClient';
import VideoUploader from '../components/VideoUploader';
import { useJobPolling } from '../hooks/useJobPolling';
import JobStatusBadge from '../components/JobStatusBadge';

interface Project {
  id: string;
  name: string;
  description?: string;
  status: string;
}

interface Meeting {
  id: string;
  title: string;
  status: string;
  source_type: string;
  started_at?: string;
}

function MeetingItem({ meeting, onUploadComplete }: { meeting: Meeting, onUploadComplete: () => void }) {
  const { jobId, setJobId, job, error: jobError } = useJobPolling(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [generateAnnotated, setGenerateAnnotated] = useState(false);

  const handleAnalyze = async () => {
    try {
      setAnalyzing(true);
      const res = await apiClient(`/meetings/${meeting.id}/analysis`, {
        method: 'POST',
        body: JSON.stringify({ pipeline: 'full', generate_annotated_video: generateAnnotated }),
      });
      if (!res.ok) {
        throw new Error('Failed to start analysis');
      }
      const data = await res.json();
      const jobId = data?.data?.job_id || data?.job_id;
      if (jobId) {
        setJobId(jobId);
      }
    } catch (err: any) {
      console.error(err);
      alert(err.message || 'Error starting analysis');
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="border p-4 rounded bg-white shadow-sm">
      <div className="flex justify-between items-start">
        <div>
          <h3 className="text-xl font-medium">{meeting.title}</h3>
          <p className="text-sm text-gray-500 mb-2">
            Status: <span className="font-semibold">{meeting.status}</span> | 
            Type: <span className="font-semibold">{meeting.source_type}</span>
          </p>
          {/* Annotated video option */}
          <label className="flex items-center gap-2 text-sm text-gray-600 mb-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={generateAnnotated}
              onChange={e => setGenerateAnnotated(e.target.checked)}
              className="w-4 h-4 rounded accent-purple-600"
            />
            <span>Generate Annotated Video <span className="text-xs text-gray-400">(slower, renders overlays)</span></span>
          </label>
          <div className="flex items-center space-x-4">
            <button
              onClick={handleAnalyze}
              disabled={analyzing || (!!job && !['succeeded', 'failed', 'cancelled'].includes(job.status))}
              className="bg-green-600 text-white px-3 py-1 rounded text-sm disabled:opacity-50"
            >
              {analyzing ? 'Starting...' : 'Analyze'}
            </button>
            <Link
              to={`/meetings/${meeting.id}/analysis`}
              className="bg-blue-600 text-white px-3 py-1 rounded text-sm"
            >
              View Analysis
            </Link>
            {jobId && <JobStatusBadge job={job} />}
            {jobError && <span className="text-red-500 text-sm">{jobError}</span>}
            <button
              onClick={async () => {
                if (window.confirm("Are you sure you want to delete this meeting?")) {
                  await apiClient(`/meetings/${meeting.id}`, { method: 'DELETE' });
                  onUploadComplete(); // Re-fetches the list
                }
              }}
              className="text-red-600 hover:text-red-800 border border-red-200 px-3 py-1 rounded text-sm hover:bg-red-50"
            >
              Delete
            </button>
          </div>
        </div>
      </div>
      
      {meeting.source_type === 'upload' && meeting.status === 'scheduled' && (
        <div className="mt-4 border-t pt-4">
          <VideoUploader 
            meetingId={meeting.id} 
            onUploadComplete={onUploadComplete}
          />
        </div>
      )}
    </div>
  );
}

export default function ProjectDetail() {
  const { projectId } = useParams<{ projectId: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchProjectData = async () => {
    try {
      setLoading(true);
      
      const [projRes, meetRes] = await Promise.all([
        apiClient(`/projects/${projectId}`),
        apiClient(`/meetings?project_id=${projectId}`)
      ]);

      if (!projRes.ok || !meetRes.ok) {
        throw new Error('Failed to load project details');
      }

      const projData = await projRes.json();
      const meetData = await meetRes.json();

      setProject(projData.data || projData);
      setMeetings(meetData.data || []);
    } catch (err: any) {
      setError(err.message || 'Error loading project');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (projectId) {
      fetchProjectData();
    }
  }, [projectId]);

  if (loading) return <div className="p-6">Loading project...</div>;
  if (error) return <div className="p-6 text-red-500">{error}</div>;
  if (!project) return <div className="p-6">Project not found</div>;

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">{project.name}</h1>
          {project.description && <p className="text-gray-600 mt-2">{project.description}</p>}
        </div>
        <Link 
          to={`/projects/${projectId}/meetings/new`} 
          className="bg-blue-600 text-white px-4 py-2 rounded"
        >
          New Meeting
        </Link>
      </div>

      <h2 className="text-2xl font-semibold mb-4">Meetings</h2>
      
      {meetings.length === 0 ? (
        <p className="text-gray-500">No meetings found. Create one to get started.</p>
      ) : (
        <div className="space-y-6">
          {meetings.map((meeting) => (
            <MeetingItem 
              key={meeting.id} 
              meeting={meeting} 
              onUploadComplete={fetchProjectData} 
            />
          ))}
        </div>
      )}
    </div>
  );
}
