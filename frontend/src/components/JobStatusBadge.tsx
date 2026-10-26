import type { Job } from '../hooks/useJobPolling';

interface JobStatusBadgeProps {
  job: Job | null;
}

export default function JobStatusBadge({ job }: JobStatusBadgeProps) {
  if (!job) return null;

  let bgColor = 'bg-gray-100 text-gray-800';
  if (job.status === 'succeeded') bgColor = 'bg-green-100 text-green-800';
  else if (job.status === 'failed') bgColor = 'bg-red-100 text-red-800';
  else if (job.status === 'running') bgColor = 'bg-blue-100 text-blue-800';
  else if (job.status === 'queued') bgColor = 'bg-yellow-100 text-yellow-800';

  return (
    <div className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${bgColor}`}>
      <span className="capitalize">{job.status}</span>
      {job.status === 'running' && job.progress_pct !== undefined && job.progress_pct !== null && (
        <span className="ml-1">({Math.round(job.progress_pct)}%)</span>
      )}
    </div>
  );
}
