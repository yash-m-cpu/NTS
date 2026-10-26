import React from 'react';

interface MetricCardProps {
  label: string;
  value: string | number;
  delta?: string;
  deltaType?: 'normal' | 'inverse' | 'off';
  caption?: string;
  icon?: React.ReactNode;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  delta,
  deltaType = 'normal',
  caption,
  icon
}) => {
  const getDeltaBadge = () => {
    if (!delta) return null;
    let bg = 'bg-slate-800 text-slate-300 border-slate-700';
    if (deltaType === 'normal') {
      bg = 'bg-emerald-950/80 text-emerald-400 border-emerald-500/30';
    } else if (deltaType === 'inverse') {
      bg = 'bg-rose-950/80 text-rose-400 border-rose-500/30';
    }

    return (
      <span className={`inline-block text-xs font-semibold px-2 py-0.5 rounded border ${bg}`}>
        {delta}
      </span>
    );
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm hover:border-slate-700 transition-colors">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">{label}</span>
        {icon && <div className="text-slate-400">{icon}</div>}
      </div>
      <div className="flex items-baseline gap-2.5 my-1">
        <span className="text-2xl font-bold text-slate-100 tracking-tight">{value}</span>
        {getDeltaBadge()}
      </div>
      {caption && <p className="text-xs text-slate-400 mt-1 leading-snug">{caption}</p>}
    </div>
  );
};
