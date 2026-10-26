import React, { useState } from 'react';
import { Upload, X, Loader2, FileVideo } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { cctvApi } from '../../../../services/cctvApi';

export const VideoUploadModal: React.FC = () => {
  const { isUploadModalOpen, setIsUploadModalOpen, selectedCamera, setActiveAnalyzedVideo } = useApp();
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  if (!isUploadModalOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setStatusMessage(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setStatusMessage(null);

    try {
      const res = await cctvApi.uploadVideo(file, selectedCamera);
      if (res && res.status === 'UPLOADED') {
        setActiveAnalyzedVideo(file.name);
        setStatusMessage({
          type: 'success',
          text: `Successfully uploaded ${file.name} and bound to ${selectedCamera} pipeline!`
        });
        setTimeout(() => {
          setIsUploadModalOpen(false);
          setFile(null);
          setStatusMessage(null);
        }, 1500);
      } else {
        setStatusMessage({
          type: 'error',
          text: 'Upload failed. The backend server did not return a valid session confirmation.'
        });
      }
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: err?.response?.data?.detail || 'Network error while uploading video to backend.'
      });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg bg-white border border-gray-200 rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gray-50">
          <div className="flex items-center gap-2">
            <Upload className="w-5 h-5 text-blue-600" />
            <h3 className="text-base font-semibold text-gray-900">Upload Workplace Video Footage</h3>
          </div>
          <button
            onClick={() => setIsUploadModalOpen(false)}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          <p className="text-xs text-gray-500 leading-relaxed">
            Upload pre-recorded CCTV footage (<code className="text-blue-600 bg-blue-50 px-1 py-0.5 rounded">.mp4, .avi, .mov, .mkv</code>) to analyze
            workstation presence, activity transitions, and workflow efficiency for <b>{selectedCamera}</b>.
          </p>

          <label className="flex flex-col items-center justify-center w-full h-40 border-2 border-dashed border-gray-300 hover:border-blue-500 rounded-xl cursor-pointer bg-gray-50/50 hover:bg-blue-50/20 transition-all p-4 text-center">
            <FileVideo className="w-10 h-10 text-gray-400 mb-2" />
            <span className="text-sm font-medium text-gray-700">
              {file ? file.name : 'Click to select or drag video file here'}
            </span>
            <span className="text-xs text-gray-400 mt-1">
              {file ? `${(file.size / (1024 * 1024)).toFixed(1)} MB` : 'Supported: MP4, AVI, MOV (up to 500MB)'}
            </span>
            <input
              type="file"
              accept="video/mp4,video/avi,video/quicktime,video/x-matroska"
              onChange={handleFileChange}
              className="hidden"
            />
          </label>

          {statusMessage && (
            <div
              className={`p-3 rounded-lg text-xs flex items-center gap-2 ${
                statusMessage.type === 'success'
                  ? 'bg-emerald-50 border border-emerald-200 text-emerald-800'
                  : 'bg-rose-50 border border-rose-200 text-rose-800'
              }`}
            >
              <span>{statusMessage.text}</span>
            </div>
          )}

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              onClick={() => setIsUploadModalOpen(false)}
              className="px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              disabled={!file || uploading}
              onClick={handleUpload}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-semibold rounded-lg shadow-sm transition-colors"
            >
              {uploading && <Loader2 className="w-4 h-4 animate-spin" />}
              <span>{uploading ? 'Uploading...' : 'Process Video'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
