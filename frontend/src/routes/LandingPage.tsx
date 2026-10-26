import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Video,
  Brain,
  Layers,
  Shield,
  ArrowRight,
  CheckCircle2,
  Server,
  Cpu,
  Lock,
  ExternalLink,
  BarChart3,
  Compass,
  FileText
} from 'lucide-react';
import { cctvApi } from '../services/cctvApi';
import { useAuthStore } from '../state/authStore';

export const LandingPage: React.FC = () => {
  const { accessToken } = useAuthStore();
  const [cctvOnline, setCctvOnline] = useState<boolean | null>(null);
  const [ntsOnline, setNtsOnline] = useState<boolean | null>(null);
  const [cctvVersion, setCctvVersion] = useState<string>('1.0.0');

  useEffect(() => {
    // Check CCTV backend health
    cctvApi.getHealth().then((h) => {
      if (h && h.status === 'HEALTHY') {
        setCctvOnline(true);
        if (h.version) setCctvVersion(h.version);
      } else {
        setCctvOnline(false);
      }
    }).catch(() => setCctvOnline(false));

    // Check Skill Analysis API health via fetch to /openapi.json
    fetch('/openapi.json')
      .then((res) => {
        setNtsOnline(res.ok);
      })
      .catch(() => {
        setNtsOnline(false);
      });
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 flex flex-col font-sans selection:bg-blue-100 selection:text-blue-900">
      {/* Top Universal Navbar */}
      <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-md border-b border-gray-200 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-blue-600 rounded-lg text-white shadow-xs">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <span className="font-bold text-base sm:text-lg text-gray-900 tracking-tight">
                Enterprise Intelligence Platform
              </span>
              <span className="hidden sm:inline-block ml-2 px-2 py-0.5 text-[10px] font-bold uppercase rounded bg-blue-50 text-blue-700 border border-blue-200">
                Unified Portal
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-3 text-xs">
            {/* Health Indicators */}
            <div className="hidden md:flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-gray-100 border border-gray-200 text-gray-600">
              <div className="flex items-center gap-1.5">
                <span className={`w-2 h-2 rounded-full ${ntsOnline ? 'bg-emerald-500' : ntsOnline === false ? 'bg-amber-500' : 'bg-gray-400'}`} />
                <span className="font-medium">NTS Core: {ntsOnline ? 'Online' : 'Standby'}</span>
              </div>
              <span className="text-gray-300">|</span>
              <div className="flex items-center gap-1.5">
                <span className={`w-2 h-2 rounded-full ${cctvOnline ? 'bg-emerald-500' : cctvOnline === false ? 'bg-amber-500' : 'bg-gray-400'}`} />
                <span className="font-medium">CCTV Engine: {cctvOnline ? 'Online' : 'Standby'}</span>
              </div>
            </div>

            <Link
              to="/cctv"
              className="text-gray-600 hover:text-blue-600 font-medium px-3 py-1.5 rounded-lg hover:bg-gray-100 transition-colors"
            >
              CCTV Analytics
            </Link>

            <Link
              to={accessToken ? "/dashboard" : "/login"}
              className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg shadow-xs transition-colors flex items-center gap-1.5"
            >
              <span>{accessToken ? "Skill Analysis" : "Sign In"}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative overflow-hidden pt-12 pb-16 lg:pt-16 lg:pb-20 border-b border-gray-200 bg-white">
        <div className="absolute inset-0 bg-gradient-to-b from-blue-50/40 via-transparent to-transparent pointer-events-none" />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative">
          <div className="text-center max-w-3xl mx-auto space-y-4">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 border border-blue-200 text-blue-700 text-xs font-semibold">
              <Shield className="w-3.5 h-3.5 text-blue-600" />
              <span>Enterprise Privacy & Operational Intelligence Suite</span>
            </div>

            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-gray-900 tracking-tight leading-tight">
              One Unified Platform. <br />
              <span className="text-blue-600">Two Specialized Analytical Engines.</span>
            </h1>

            <p className="text-sm sm:text-base text-gray-600 leading-relaxed max-w-2xl mx-auto">
              Seamlessly integrated workplace intelligence: monitor physical spatial utilization and workflow bottlenecks via computer vision, alongside multimodal meeting behavioral dynamics and non-technical skill assessments.
            </p>
          </div>
        </div>
      </section>

      {/* Main Dual Product Branching Grid */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-12">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-stretch">

          {/* CARD 1: CCTV Workplace Analytics */}
          <div className="bg-white border-2 border-gray-200 hover:border-blue-400 rounded-2xl p-6 sm:p-8 flex flex-col justify-between shadow-xs hover:shadow-md transition-all group">
            <div className="space-y-6">
              {/* Product Header */}
              <div className="flex items-start justify-between gap-4">
                <div className="p-3 bg-blue-50 border border-blue-200 rounded-xl text-blue-600 group-hover:bg-blue-600 group-hover:text-white transition-colors">
                  <Video className="w-7 h-7" />
                </div>
                <div className="text-right">
                  <span className="px-2.5 py-1 text-xs font-bold uppercase rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                    Product Branch A
                  </span>
                  <div className="text-[11px] text-gray-400 font-mono mt-1">
                    v{cctvVersion} • Port 8001
                  </div>
                </div>
              </div>

              {/* Title & Description */}
              <div>
                <h2 className="text-2xl font-bold text-gray-900 group-hover:text-blue-600 transition-colors">
                  CCTV Analytics
                </h2>
                <p className="text-xs font-semibold text-blue-600 uppercase tracking-wider mt-1">
                  Workplace Productivity & Workflow Intelligence System
                </p>
                <p className="text-xs sm:text-sm text-gray-600 mt-2 leading-relaxed">
                  Understand physical workplace activity, space utilization, and workflow bottlenecks through video-based operational analytics with strict privacy covenants.
                </p>
              </div>

              {/* Feature Checklist */}
              <div className="space-y-2.5 pt-2 border-t border-gray-100">
                <span className="text-xs font-bold text-gray-500 uppercase tracking-wider block mb-1">
                  Verified Operational Capabilities:
                </span>
                
                <div className="flex items-start gap-2 text-xs text-gray-700">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <span><b>Person Detection & Tracking:</b> Ephemeral salted hashing (<code className="text-blue-600 font-mono">TRK-xxxx</code>) rotated daily at 00:00 UTC.</span>
                </div>

                <div className="flex items-start gap-2 text-xs text-gray-700">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <span><b>Live Annotated CCTV Stream:</b> MJPEG video player with LOD toggles for polygons, centroids, and activity pills.</span>
                </div>

                <div className="flex items-start gap-2 text-xs text-gray-700">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <span><b>Activity & Posture Distribution:</b> 7 standardized biomechanical activity classes with sedentary lock warnings (Scorecard B).</span>
                </div>

                <div className="flex items-start gap-2 text-xs text-gray-700">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <span><b>Workstation Occupancy (WOR):</b> Objective space rightsizing metrics with debounced transitory departures (Scorecard C).</span>
                </div>

                <div className="flex items-start gap-2 text-xs text-gray-700">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <span><b>Workflow Bottleneck Analysis:</b> Circulation flows (Sankey), corridor congestion, and focus interruption rates (Scorecard A).</span>
                </div>

                <div className="flex items-start gap-2 text-xs text-gray-700">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <span><b>Interactive Polygon Zone Editor:</b> Normalized floating-point vertices <code className="text-blue-600 font-mono">[0.0, 1.0]</code> with live database persistence.</span>
                </div>

                <div className="flex items-start gap-2 text-xs text-gray-700">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <span><b>Privacy-Preserving MP4 Export:</b> DPO dual-control gated video exports with automatic face & credential redaction.</span>
                </div>
              </div>
            </div>

            {/* Actions & Direct Route Shortcuts */}
            <div className="pt-6 mt-6 border-t border-gray-100 space-y-3">
              <Link
                to="/cctv"
                className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl shadow-xs flex items-center justify-center gap-2 group-hover:gap-3 transition-all"
              >
                <span>Launch CCTV Analytics</span>
                <ArrowRight className="w-4 h-4" />
              </Link>

              <div className="flex flex-wrap items-center justify-center gap-2 text-[11px] text-gray-500 pt-1">
                <span className="font-semibold text-gray-400">Quick Jump:</span>
                <Link to="/cctv" className="text-blue-600 hover:underline">01. Live CCTV</Link>
                <span>•</span>
                <Link to="/cctv/view02" className="text-blue-600 hover:underline">02. Tracks</Link>
                <span>•</span>
                <Link to="/cctv/view03" className="text-blue-600 hover:underline">03. Efficiency</Link>
                <span>•</span>
                <Link to="/cctv/view05" className="text-blue-600 hover:underline">05. Occupancy</Link>
                <span>•</span>
                <Link to="/cctv/zones" className="text-blue-600 hover:underline">Zone Editor</Link>
              </div>
            </div>
          </div>

          {/* CARD 2: Skill Analysis Platform */}
          <div className="bg-white border-2 border-gray-200 hover:border-blue-400 rounded-2xl p-6 sm:p-8 flex flex-col justify-between shadow-xs hover:shadow-md transition-all group">
            <div className="space-y-6">
              {/* Product Header */}
              <div className="flex items-start justify-between gap-4">
                <div className="p-3 bg-blue-50 border border-blue-200 rounded-xl text-blue-600 group-hover:bg-blue-600 group-hover:text-white transition-colors">
                  <Brain className="w-7 h-7" />
                </div>
                <div className="text-right">
                  <span className="px-2.5 py-1 text-xs font-bold uppercase rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                    Product Branch B
                  </span>
                  <div className="text-[11px] text-gray-400 font-mono mt-1">
                    FastAPI + ARQ • Port 8000
                  </div>
                </div>
              </div>

              {/* Title & Description */}
              <div>
                <h2 className="text-2xl font-bold text-gray-900 group-hover:text-blue-600 transition-colors">
                  Skill Analysis
                </h2>
                <p className="text-xs font-semibold text-blue-600 uppercase tracking-wider mt-1">
                  NTS Multi-Modal Meeting Intelligence Platform
                </p>
                <p className="text-xs sm:text-sm text-gray-600 mt-2 leading-relaxed">
                  Evaluate collaborative effectiveness, non-technical skills (NTS), speech dynamics, and participant interaction patterns across organizational meetings.
                </p>
              </div>

              {/* Feature Checklist */}
              <div className="space-y-2.5 pt-2 border-t border-gray-100">
                <span className="text-xs font-bold text-gray-500 uppercase tracking-wider block mb-1">
                  Verified Operational Capabilities:
                </span>

                <div className="flex items-start gap-2 text-xs text-gray-700">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <span><b>Multi-Modal Video Ingestion:</b> Chunked presigned S3 upload to MinIO with MIME validation and background processing jobs.</span>
                </div>

                <div className="flex items-start gap-2 text-xs text-gray-700">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <span><b>Visual Feature Extraction:</b> Multi-person face pose (yaw, pitch, roll), gaze bearing, emotion distribution, and body landmarks.</span>
                </div>

                <div className="flex items-start gap-2 text-xs text-gray-700">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <span><b>Speech & Language Analytics:</b> Faster-Whisper automated transcription, speech ratios, turn taking, and speaking duration tracking.</span>
                </div>

                <div className="flex items-start gap-2 text-xs text-gray-700">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <span><b>Participant Interaction Graphs:</b> Pairwise conversational exchange matrices, quick responses, and directional dialogue flows.</span>
                </div>

                <div className="flex items-start gap-2 text-xs text-gray-700">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <span><b>Non-Technical Skill (NTS) Scoring:</b> Machine learning behavioral scoring across communication, decision-making, and leadership.</span>
                </div>

                <div className="flex items-start gap-2 text-xs text-gray-700">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <span><b>Annotated Video Playback:</b> Real-time synchronized visual telemetry timeline aligned with participant utterances.</span>
                </div>

                <div className="flex items-start gap-2 text-xs text-gray-700">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <span><b>Comprehensive Executive Reports:</b> Automated PDF report generation with structured non-technical skill scorecards.</span>
                </div>
              </div>
            </div>

            {/* Actions & Direct Route Shortcuts */}
            <div className="pt-6 mt-6 border-t border-gray-100 space-y-3">
              <Link
                to={accessToken ? "/dashboard" : "/login"}
                className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl shadow-xs flex items-center justify-center gap-2 group-hover:gap-3 transition-all"
              >
                <span>{accessToken ? "Enter Skill Analysis Dashboard" : "Sign In to Skill Analysis"}</span>
                <ArrowRight className="w-4 h-4" />
              </Link>

              <div className="flex flex-wrap items-center justify-center gap-2 text-[11px] text-gray-500 pt-1">
                <span className="font-semibold text-gray-400">Quick Jump:</span>
                <Link to="/dashboard" className="text-blue-600 hover:underline">Dashboard</Link>
                <span>•</span>
                <Link to="/login" className="text-blue-600 hover:underline">Login</Link>
                <span>•</span>
                <Link to="/register" className="text-blue-600 hover:underline">Register</Link>
                <span>•</span>
                <a href="/docs" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline inline-flex items-center gap-0.5">
                  <span>API Docs</span>
                  <ExternalLink className="w-2.5 h-2.5" />
                </a>
              </div>
            </div>
          </div>
        </div>

        {/* Unified Architecture & Engineering Guarantees */}
        <div className="mt-16 bg-white border border-gray-200 rounded-2xl p-6 sm:p-8 shadow-xs">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-gray-100 pb-5">
            <div>
              <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                <Cpu className="w-5 h-5 text-blue-600" />
                <span>Unified Platform Technical Architecture</span>
              </h3>
              <p className="text-xs text-gray-500 mt-0.5">
                Two independently scalable analytical services harmonized under one modern React frontend.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                Zero-Coupling Decoupled Backends
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 pt-6 text-xs">
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-gray-900 font-semibold">
                <Server className="w-4 h-4 text-blue-600" />
                <span>Independent Micro-Engines</span>
              </div>
              <p className="text-gray-500 leading-relaxed">
                Skill Analysis runs on port 8000 (FastAPI, ARQ, PostgreSQL, MinIO), while CCTV Analytics runs on port 8001 (FastAPI, OpenCV, YOLO). Both are proxied seamlessly via Vite.
              </p>
            </div>

            <div className="space-y-2">
              <div className="flex items-center gap-2 text-gray-900 font-semibold">
                <Lock className="w-4 h-4 text-emerald-600" />
                <span>Dual Anti-Surveillance Covenants</span>
              </div>
              <p className="text-gray-500 leading-relaxed">
                Biometric face recognition and individual punitive rankings are strictly banned. CCTV uses ephemeral salted daily hashes; Skill Analysis uses anonymized participant tracks.
              </p>
            </div>

            <div className="space-y-2">
              <div className="flex items-center gap-2 text-gray-900 font-semibold">
                <BarChart3 className="w-4 h-4 text-amber-600" />
                <span>Harmonized Design System</span>
              </div>
              <p className="text-gray-500 leading-relaxed">
                Both products strictly adopt the Skill Analysis light theme design system: Tailwind CSS tokens, consistent card elevation, blue interactive accents, and unified responsive navigation.
              </p>
            </div>

            <div className="space-y-2">
              <div className="flex items-center gap-2 text-gray-900 font-semibold">
                <Compass className="w-4 h-4 text-purple-600" />
                <span>Bi-Directional Navigation</span>
              </div>
              <p className="text-gray-500 leading-relaxed">
                Users can transition seamlessly between CCTV spatial views and meeting assessment views, and return to this central portal at any time without application restarts.
              </p>
            </div>
          </div>
        </div>

        {/* Integration Documentation Reference Banner */}
        <div className="mt-8 p-4 rounded-xl bg-blue-50/60 border border-blue-200/80 flex flex-wrap items-center justify-between gap-4 text-xs">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-600 rounded-lg text-white">
              <FileText className="w-4 h-4" />
            </div>
            <div>
              <span className="font-bold text-gray-900">Integration Documentation Suite Available</span>
              <p className="text-gray-600">
                Audit specs generated in <code className="text-blue-700 font-mono bg-blue-100/60 px-1 py-0.5 rounded">docs/integration/</code>: Project Audit, Feature Parity Matrix, Unified Architecture, and Roadmap.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3 text-xs font-semibold text-blue-700">
            <span>Enterprise Multi-Modal Release</span>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 py-6 text-center text-xs text-gray-500">
        <div className="max-w-7xl mx-auto px-4 space-y-1">
          <p className="font-medium text-gray-700">
            Enterprise Workplace & Meeting Intelligence Platform
          </p>
          <p className="text-gray-400 text-[11px]">
            Skill Analysis Platform • CCTV Workplace Productivity & Workflow Intelligence System
          </p>
        </div>
      </footer>
    </div>
  );
};
