import React, { useState } from 'react';
import { apiClient } from '../lib/apiClient';

interface VideoUploaderProps {
  meetingId: string;
  onUploadComplete?: () => void;
}

export default function VideoUploader({ meetingId, onUploadComplete }: VideoUploaderProps) {
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState<number>(0);
  const [status, setStatus] = useState<'idle' | 'initiating' | 'uploading' | 'completing' | 'success' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState<string>('');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    try {
      setStatus('initiating');
      setErrorMessage('');

      // 1. Initiate upload
      const initRes = await apiClient('/media/uploads/initiate', {
        method: 'POST',
        body: JSON.stringify({
          meeting_id: meetingId,
          asset_type: 'video',
          content_type: file.type,
          size_bytes: file.size,
        }),
      });

      if (!initRes.ok) {
        throw new Error('Failed to initiate upload');
      }

      const { data } = await initRes.json();
      const { media_asset_id, upload_url } = data;

      setStatus('uploading');

      // 2. Upload using XMLHttpRequest to track progress
      await new Promise<void>((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('PUT', upload_url, true);
        xhr.setRequestHeader('Content-Type', file.type);

        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            const percentComplete = Math.round((event.loaded / event.total) * 100);
            setProgress(percentComplete);
          }
        };

        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve();
          } else {
            reject(new Error('Upload to storage failed'));
          }
        };

        xhr.onerror = () => reject(new Error('Network error during upload'));

        xhr.send(file);
      });

      setStatus('completing');

      // 3. Complete upload
      const compRes = await apiClient(`/media/uploads/${media_asset_id}/complete`, {
        method: 'POST',
      });

      if (!compRes.ok) {
        throw new Error('Failed to complete upload');
      }

      setStatus('success');
      if (onUploadComplete) {
        onUploadComplete();
      }

    } catch (err: any) {
      setStatus('error');
      setErrorMessage(err.message || 'An error occurred during upload');
    }
  };

  return (
    <div className="video-uploader p-4 border rounded mt-4">
      <h3 className="text-lg font-semibold mb-2">Upload Video</h3>
      <input 
        type="file" 
        accept="video/mp4,video/quicktime,video/webm,audio/mpeg,audio/wav" 
        onChange={handleFileChange} 
        disabled={status !== 'idle' && status !== 'error'}
        className="mb-4 block"
      />
      
      {status === 'idle' || status === 'error' ? (
        <button 
          onClick={handleUpload} 
          disabled={!file}
          className="bg-blue-500 text-white px-4 py-2 rounded disabled:bg-gray-400"
        >
          Upload
        </button>
      ) : null}

      {status !== 'idle' && status !== 'error' && (
        <div className="mt-4">
          <p>Status: {status}</p>
          <div className="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700 mt-2">
            <div className="bg-blue-600 h-2.5 rounded-full" style={{ width: `${progress}%` }}></div>
          </div>
          <p className="text-sm mt-1">{progress}%</p>
        </div>
      )}

      {status === 'error' && (
        <p className="text-red-500 mt-2">{errorMessage}</p>
      )}

      {status === 'success' && (
        <p className="text-green-500 mt-2">Upload completed successfully!</p>
      )}
    </div>
  );
}
