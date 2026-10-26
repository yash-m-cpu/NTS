import React, { useEffect, useState } from 'react';
import { useApp } from '../context/AppContext';
import { apiService } from '../services/api';
import type { SpatialZone } from '../types';
import { DataTable, type Column } from '../components/common/DataTable';
import { Plus, Trash2, CheckCircle2, AlertCircle, Save } from 'lucide-react';

export const ZoneEditor: React.FC = () => {
  const { selectedCamera } = useApp();
  const [zones, setZones] = useState<SpatialZone[]>([]);
  const [activeTab, setActiveTab] = useState<'add' | 'delete'>('add');

  // Add Form State
  const [zoneId, setZoneId] = useState('POD-03');
  const [zoneName, setZoneName] = useState('Engineering Pod 3');
  const [zoneType, setZoneType] = useState<SpatialZone['zone_type']>('WORKSTATION');
  const [capacity, setCapacity] = useState<number>(2);
  const [cameraId, setCameraId] = useState<string>(selectedCamera);
  const [coordsText, setCoordsText] = useState(
    '[\n  [0.10, 0.20],\n  [0.45, 0.20],\n  [0.45, 0.70],\n  [0.10, 0.70]\n]'
  );

  // Delete Form State
  const [deleteZoneId, setDeleteZoneId] = useState<string>('');

  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const fetchZones = async () => {
    const list = await apiService.getZones(selectedCamera);
    setZones(list);
    if (list.length > 0 && !deleteZoneId) {
      setDeleteZoneId(list[0].zone_id);
    }
  };

  useEffect(() => {
    fetchZones();
    setCameraId(selectedCamera);
  }, [selectedCamera]);

  const handleSaveZone = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(null);

    let parsedCoords: any;
    try {
      parsedCoords = JSON.parse(coordsText);
    } catch (err: any) {
      setMessage({ type: 'error', text: `Invalid JSON syntax in coordinates: ${err.message}` });
      return;
    }

    if (!Array.isArray(parsedCoords) || parsedCoords.length < 3) {
      setMessage({ type: 'error', text: 'Validation Error: Polygon must contain a list of at least 3 coordinate pairs.' });
      return;
    }
    if (parsedCoords.length > 12) {
      setMessage({ type: 'error', text: 'Validation Error: Maximum 12 vertices allowed per zone.' });
      return;
    }

    const valid = parsedCoords.every(
      (pt) =>
        Array.isArray(pt) &&
        pt.length === 2 &&
        typeof pt[0] === 'number' &&
        typeof pt[1] === 'number' &&
        pt[0] >= 0.0 &&
        pt[0] <= 1.0 &&
        pt[1] >= 0.0 &&
        pt[1] <= 1.0
    );

    if (!valid) {
      setMessage({ type: 'error', text: 'Coordinates must be floating point numbers within [0.0, 1.0].' });
      return;
    }

    setLoading(true);
    try {
      const payload: Partial<SpatialZone> = {
        zone_id: zoneId.trim(),
        camera_id: cameraId.trim(),
        name: zoneName.trim(),
        zone_type: zoneType,
        capacity: Number(capacity),
        polygon_coords: parsedCoords
      };

      const res = await apiService.createZone(payload);
      if (res) {
        setMessage({ type: 'success', text: `Zone '${zoneId}' saved successfully!` });
        await fetchZones();
      }
    } catch (err: any) {
      setMessage({ type: 'error', text: err?.response?.data?.detail || 'Failed to save zone definition with backend.' });
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteZone = async () => {
    if (!deleteZoneId) return;
    setLoading(true);
    setMessage(null);

    try {
      const ok = await apiService.deleteZone(deleteZoneId, selectedCamera);
      if (ok) {
        setMessage({ type: 'success', text: `Zone '${deleteZoneId}' deleted successfully.` });
        await fetchZones();
      } else {
        setMessage({ type: 'error', text: `Failed to delete zone '${deleteZoneId}'.` });
      }
    } catch (err: any) {
      setMessage({ type: 'error', text: err?.message || 'Error deleting zone.' });
    } finally {
      setLoading(false);
    }
  };

  const columns: Column<SpatialZone>[] = [
    { header: 'Zone ID', accessorKey: 'zone_id', className: 'font-mono text-sky-400 font-bold' },
    { header: 'Display Name', accessorKey: 'name' },
    {
      header: 'Type',
      cell: (row) => (
        <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-800 text-slate-300 border border-slate-700">
          {row.zone_type}
        </span>
      )
    },
    { header: 'Capacity', accessorKey: 'capacity', className: 'font-mono' },
    { header: 'Camera', accessorKey: 'camera_id', className: 'font-mono' },
    {
      header: 'Vertices Count',
      cell: (row) => <span className="font-mono">{row.polygon_coords?.length || 0} pts</span>
    },
    {
      header: 'Sample Coordinates [0.0, 1.0]',
      cell: (row) => {
        const coords = row.polygon_coords || [];
        const sample = coords.slice(0, 4).map((p) => `(${p[0].toFixed(2)}, ${p[1].toFixed(2)})`).join(', ');
        return <span className="font-mono text-xs text-slate-400">{sample}{coords.length > 4 ? '...' : ''}</span>;
      }
    }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
          <span>📐 Interactive Spatial Zone & Polygon Editor</span>
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Define and calibrate spatial regions of interest (workstations, corridors, collaboration spaces).
          Coordinates are stored as normalized floats <code className="text-sky-300">[0.0, 1.0]</code>, completely eliminating truncation errors (<code className="text-sky-300">BUG-02</code>).
        </p>
      </div>

      {/* Currently Configured Zones Table */}
      <div className="space-y-3">
        <h4 className="text-sm font-semibold text-slate-200">🗺️ Currently Configured Zones</h4>
        <DataTable columns={columns} data={zones} emptyMessage="No spatial zones configured yet for this camera." />
      </div>

      {/* Tabs */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
        <div className="flex border-b border-slate-800 bg-slate-950/60">
          <button
            onClick={() => { setActiveTab('add'); setMessage(null); }}
            className={`flex items-center gap-2 px-6 py-3 text-xs font-semibold transition-colors border-b-2 ${
              activeTab === 'add'
                ? 'border-sky-500 text-sky-300 bg-slate-900/50'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Plus className="w-4 h-4" />
            <span>Add / Update Zone</span>
          </button>
          <button
            onClick={() => { setActiveTab('delete'); setMessage(null); }}
            className={`flex items-center gap-2 px-6 py-3 text-xs font-semibold transition-colors border-b-2 ${
              activeTab === 'delete'
                ? 'border-rose-500 text-rose-300 bg-slate-900/50'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Trash2 className="w-4 h-4" />
            <span>Delete Zone</span>
          </button>
        </div>

        <div className="p-6">
          {message && (
            <div
              className={`p-3 rounded-lg text-xs flex items-center gap-2 mb-4 ${
                message.type === 'success'
                  ? 'bg-emerald-950/80 border border-emerald-500/30 text-emerald-300'
                  : 'bg-rose-950/80 border border-rose-500/30 text-rose-300'
              }`}
            >
              {message.type === 'success' ? (
                <CheckCircle2 className="w-4 h-4 shrink-0" />
              ) : (
                <AlertCircle className="w-4 h-4 shrink-0" />
              )}
              <span>{message.text}</span>
            </div>
          )}

          {activeTab === 'add' ? (
            <form onSubmit={handleSaveZone} className="space-y-4 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="text-slate-400 block mb-1">Zone ID (e.g. POD-01, DESK-03)</label>
                  <input
                    type="text"
                    value={zoneId}
                    onChange={(e) => setZoneId(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded-lg px-3 py-2 font-mono focus:outline-none focus:border-sky-500"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">Display Name</label>
                  <input
                    type="text"
                    value={zoneName}
                    onChange={(e) => setZoneName(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:border-sky-500"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">Zone Type</label>
                  <select
                    value={zoneType}
                    onChange={(e) => setZoneType(e.target.value as any)}
                    className="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:border-sky-500"
                  >
                    <option value="WORKSTATION">WORKSTATION</option>
                    <option value="COLLABORATION">COLLABORATION</option>
                    <option value="CORRIDOR">CORRIDOR</option>
                    <option value="FOCUS_ROOM">FOCUS_ROOM</option>
                    <option value="SERVICE_RESOURCE">SERVICE_RESOURCE</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-slate-400 block mb-1">Design Capacity (persons)</label>
                  <input
                    type="number"
                    min="1"
                    max="20"
                    value={capacity}
                    onChange={(e) => setCapacity(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded-lg px-3 py-2 font-mono focus:outline-none focus:border-sky-500"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">Target Camera ID</label>
                  <input
                    type="text"
                    value={cameraId}
                    onChange={(e) => setCameraId(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded-lg px-3 py-2 font-mono focus:outline-none focus:border-sky-500"
                  />
                </div>
              </div>

              <div>
                <label className="text-slate-400 block mb-1">
                  Polygon Vertices (Normalized Float Coordinates in [0.0, 1.0])
                </label>
                <p className="text-[11px] text-slate-500 mb-2">
                  Provide at least 3 vertices (e.g. [[0.1, 0.2], [0.4, 0.2], [0.4, 0.6], [0.1, 0.6]]):
                </p>
                <textarea
                  rows={5}
                  value={coordsText}
                  onChange={(e) => setCoordsText(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 text-sky-300 font-mono text-xs rounded-lg p-3 leading-relaxed focus:outline-none focus:border-sky-500"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white font-semibold rounded-lg shadow transition-colors"
              >
                <Save className="w-4 h-4" />
                <span>Save Zone Definition</span>
              </button>
            </form>
          ) : (
            <div className="space-y-4 text-xs max-w-md">
              <label className="text-slate-400 block mb-1">Select Zone to Remove</label>
              <select
                value={deleteZoneId}
                onChange={(e) => setDeleteZoneId(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded-lg px-3 py-2 font-mono"
              >
                {zones.map((z) => (
                  <option key={z.zone_id} value={z.zone_id}>
                    {z.zone_id} ({z.name} - {z.zone_type})
                  </option>
                ))}
              </select>

              <button
                onClick={handleDeleteZone}
                disabled={loading || !deleteZoneId}
                className="inline-flex items-center gap-2 px-4 py-2 bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white font-semibold rounded-lg shadow transition-colors"
              >
                <Trash2 className="w-4 h-4" />
                <span>Confirm Zone Deletion</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
