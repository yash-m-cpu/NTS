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
    let bg = 'bg-gray-100 text-gray-700 border-gray-200';
    if (deltaType === 'normal') {
      bg = 'bg-emerald-50 text-emerald-700 border-emerald-200';
    } else if (deltaType === 'inverse') {
      bg = 'bg-rose-50 text-rose-700 border-rose-200';
    }

    return (
      <span className={`inline-block text-xs font-semibold px-2 py-0.5 rounded border ${bg}`}>
        {delta}
      </span>
    );
  };

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm hover:border-blue-300 transition-all">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">{label}</span>
        {icon && <div className="text-gray-400">{icon}</div>}
      </div>
      <div className="flex items-baseline gap-2.5 my-1">
        <span className="text-2xl font-bold text-gray-900 tracking-tight">{value}</span>
        {getDeltaBadge()}
      </div>
      {caption && <p className="text-xs text-gray-500 mt-1 leading-snug">{caption}</p>}
    </div>
  );
};
