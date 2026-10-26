import React from 'react';
import { ShieldCheck } from 'lucide-react';

interface CovenantBadgeProps {
  className?: string;
}

export const CovenantBadge: React.FC<CovenantBadgeProps> = ({ className = '' }) => {
  return (
    <div
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-emerald-950/60 border border-emerald-500/30 text-emerald-300 text-xs font-medium tracking-wide shadow-sm ${className}`}
    >
      <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
      <span>Anti-Surveillance Covenant Active</span>
    </div>
  );
};
