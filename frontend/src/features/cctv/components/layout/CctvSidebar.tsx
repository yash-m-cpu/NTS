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
  PenTool,
  Home
} from 'lucide-react';

const navigationItems = [
  {
    path: '/cctv',
    label: '01. Live Annotated CCTV',
    icon: Video,
    badge: 'Live',
    end: true
  },
  {
    path: '/cctv/view02',
    label: '02. Ephemeral Track Details',
    icon: UserCheck
  },
  {
    path: '/cctv/view03',
    label: '03. Workflow Efficiency (Scorecard A)',
    icon: Zap
  },
  {
    path: '/cctv/view04',
    label: '04. Activity Distribution (Scorecard B)',
    icon: BarChart3
  },
  {
    path: '/cctv/view05',
    label: '05. Occupancy & Presence (Scorecard C)',
    icon: Building2
  },
  {
    path: '/cctv/view06',
    label: '06. Output Effectiveness (Scorecard D)',
    icon: CheckSquare
  },
  {
    path: '/cctv/view07',
    label: '07. Team & Workspace Overview',
    icon: Users
  },
  {
    path: '/cctv/view08',
    label: '08. Historical Trend Comparison',
    icon: GitCompare
  },
  {
    path: '/cctv/view09',
    label: '09. Video Export Controls',
    icon: Film
  },
  {
    path: '/cctv/view10',
    label: '10. Data Quality & Model Health',
    icon: Activity
  },
  {
    path: '/cctv/zones',
    label: 'Interactive Zone Editor',
    icon: PenTool
  }
];

export const CctvSidebar: React.FC = () => {
  return (
    <aside className="w-72 shrink-0 bg-white border-r border-gray-200 flex flex-col justify-between p-4 min-h-[calc(100vh-65px)]">
      <div>
        <div className="px-3 py-2 mb-2 flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">
            CCTV Operational Views
          </span>
        </div>

        <nav className="space-y-1">
          {navigationItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.end}
                className={({ isActive }) =>
                  `flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-blue-50 border border-blue-200 text-blue-700 shadow-xs font-semibold'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100 border border-transparent'
                  }`
                }
              >
                <div className="flex items-center gap-2.5 truncate">
                  <Icon className="w-4 h-4 shrink-0 text-blue-600" />
                  <span className="truncate">{item.label}</span>
                </div>
                {item.badge && (
                  <span className="px-1.5 py-0.5 text-[10px] font-bold uppercase rounded bg-rose-50 text-rose-600 border border-rose-200">
                    {item.badge}
                  </span>
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Footer Info & Quick Jump */}
      <div className="pt-4 border-t border-gray-200 px-2 text-xs text-gray-500 space-y-2">
        <NavLink
          to="/"
          className="flex items-center gap-2 text-xs text-gray-600 hover:text-blue-600 font-medium py-1 transition-colors"
        >
          <Home className="w-3.5 h-3.5 text-gray-400" />
          <span>Unified Landing Page</span>
        </NavLink>
        <p className="text-[11px] text-gray-400">Enterprise Computer Vision Pipeline</p>
      </div>
    </aside>
  );
};
