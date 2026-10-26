import React from 'react';
import { ShieldCheck } from 'lucide-react';

interface CovenantBadgeProps {
  className?: string;
}

export const CovenantBadge: React.FC<CovenantBadgeProps> = ({ className = '' }) => {
  return (
    <div
      className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-medium tracking-wide shadow-sm ${className}`}
    >
      <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
      <span>Anti-Surveillance Covenant Active</span>
    </div>
  );
};
