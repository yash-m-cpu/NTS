import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  Video,
  UserCheck,
  Zap,
  BarChart3,
  Building2,
  CheckSquare,
  Users,
  GitCompare,
  Film,
  Activity,
  PenTool
} from 'lucide-react';

const navigationItems = [
  {
    path: '/',
    label: '01. Live Annotated CCTV',
    icon: Video,
    badge: 'Live'
  },
  {
    path: '/view02',
    label: '02. Ephemeral Track Details',
    icon: UserCheck
  },
  {
    path: '/view03',
    label: '03. Workflow Efficiency (Scorecard A)',
    icon: Zap
  },
  {
    path: '/view04',
    label: '04. Activity Distribution (Scorecard B)',
    icon: BarChart3
  },
  {
    path: '/view05',
    label: '05. Occupancy & Presence (Scorecard C)',
    icon: Building2
  },
  {
    path: '/view06',
    label: '06. Output Effectiveness (Scorecard D)',
    icon: CheckSquare
  },
  {
    path: '/view07',
    label: '07. Team & Workspace Overview',
    icon: Users
  },
  {
    path: '/view08',
    label: '08. Historical Trend Comparison',
    icon: GitCompare
  },
  {
    path: '/view09',
    label: '09. Video Export Controls',
    icon: Film
  },
  {
    path: '/view10',
    label: '10. Data Quality & Model Health',
    icon: Activity
  },
  {
    path: '/zones',
    label: 'Interactive Zone Editor',
    icon: PenTool
  }
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-72 shrink-0 bg-slate-950 border-r border-slate-800 flex flex-col justify-between p-4 min-h-[calc(100vh-65px)]">
      <div>
        <div className="px-3 py-2 mb-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Operational Views
          </span>
        </div>

        <nav className="space-y-1">
          {navigationItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-sky-600/15 border border-sky-500/30 text-sky-300 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900 border border-transparent'
                  }`
                }
              >
                <div className="flex items-center gap-2.5 truncate">
                  <Icon className="w-4 h-4 shrink-0 text-sky-400/80" />
                  <span className="truncate">{item.label}</span>
                </div>
                {item.badge && (
                  <span className="px-1.5 py-0.5 text-[10px] font-bold uppercase rounded bg-rose-500/20 text-rose-400 border border-rose-500/30">
                    {item.badge}
                  </span>
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Footer Info */}
      <div className="pt-4 border-t border-slate-800/80 px-2 text-[11px] text-slate-500 space-y-1">
        <p>Phase 13 Architecture</p>
        <p>Enterprise Computer Vision Pipeline</p>
      </div>
    </aside>
  );
};
