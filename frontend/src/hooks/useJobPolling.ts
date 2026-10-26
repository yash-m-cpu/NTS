import { useState, useEffect } from 'react';
import { apiClient } from '../lib/apiClient';

export interface Job {
  id: string;
  status: 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled' | string;
  progress_pct?: number;
  result?: any;
  error?: string;
  created_at?: string;
  updated_at?: string;
}

export function useJobPolling(initialJobId: string | null = null, pollingIntervalMs = 3000) {
  const [jobId, setJobId] = useState<string | null>(initialJobId);
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let timeoutId: ReturnType<typeof setTimeout>;
    let isMounted = true;

    const pollJob = async () => {
      if (!jobId) return;

      try {
        const res = await apiClient(`/jobs/${jobId}`);
        if (!res.ok) {
          throw new Error('Failed to fetch job status');
        }
        const data = await res.json();
        const currentJob = data.data || data;
        
        if (isMounted) {
          setJob(currentJob);

          const terminalStates = ['succeeded', 'failed', 'cancelled'];
          if (!terminalStates.includes(currentJob.status)) {
            timeoutId = setTimeout(pollJob, pollingIntervalMs);
          }
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || 'Error polling job');
        }
      }
    };

    if (jobId) {
      pollJob();
    }

    return () => {
      isMounted = false;
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
    };
  }, [jobId, pollingIntervalMs]);

  return { jobId, setJobId, job, error };
}
