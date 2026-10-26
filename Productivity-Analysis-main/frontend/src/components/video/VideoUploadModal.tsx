import React, { useState } from 'react';
import { Upload, X, CheckCircle, AlertCircle, Loader2, FileVideo } from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { apiService } from '../../services/api';

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
      const res = await apiService.uploadVideo(file, selectedCamera);
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/60">
          <div className="flex items-center gap-2">
            <Upload className="w-5 h-5 text-sky-400" />
            <h3 className="text-base font-semibold text-slate-100">Upload Workplace Video Footage</h3>
          </div>
          <button
            onClick={() => setIsUploadModalOpen(false)}
            className="text-slate-400 hover:text-slate-200 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          <p className="text-xs text-slate-400 leading-relaxed">
            Upload pre-recorded CCTV footage (<code className="text-sky-300">.mp4, .avi, .mov, .mkv</code>) to analyze
            workstation presence, activity transitions, and workflow efficiency for <b>{selectedCamera}</b>.
          </p>

          <label className="flex flex-col items-center justify-center w-full h-40 border-2 border-dashed border-slate-700 hover:border-sky-500 rounded-xl cursor-pointer bg-slate-950/40 hover:bg-slate-950/70 transition-all p-4 text-center">
            <FileVideo className="w-10 h-10 text-slate-500 mb-2" />
            <span className="text-sm font-medium text-slate-300">
              {file ? file.name : 'Click to select or drag video file here'}
            </span>
            <span className="text-xs text-slate-500 mt-1">
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
                  ? 'bg-emerald-950/80 border border-emerald-500/30 text-emerald-300'
                  : 'bg-rose-950/80 border border-rose-500/30 text-rose-300'
              }`}
            >
              {statusMessage.type === 'success' ? (
                <CheckCircle className="w-4 h-4 shrink-0" />
              ) : (
                <AlertCircle className="w-4 h-4 shrink-0" />
              )}
              <span>{statusMessage.text}</span>
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-800 bg-slate-950/60">
          <button
            onClick={() => setIsUploadModalOpen(false)}
            disabled={uploading}
            className="px-4 py-2 text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleUpload}
            disabled={!file || uploading}
            className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-sky-600 hover:bg-sky-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg shadow transition-colors"
          >
            {uploading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Uploading & Binding...</span>
              </>
            ) : (
              <>
                <Upload className="w-4 h-4" />
                <span>Analyze Video</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
