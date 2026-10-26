# Integration Roadmap & Execution Plan

**Project:** Unified Enterprise Video Analytics (Skill Analysis + CCTV Workplace Intelligence)  
**Execution Date:** October 20, 2026  

---

## Roadmap Phases & Execution Steps

### Phase 1: Audit & Analysis (Completed)
- [x] Inspect Skill Analysis codebase, dependencies, and operational status.
- [x] Inspect CCTV codebase, FastAPI backend, and React view structure.
- [x] Create `PROJECT_AUDIT.md`.
- [x] Create `FEATURE_PARITY_MATRIX.md`.
- [x] Create `UNIFIED_ARCHITECTURE.md`.
- [x] Create `INTEGRATION_ROADMAP.md`.

### Phase 2: Frontend Package Alignment
- [ ] Install missing dependencies in `c:/PJT/frontend`:
  - `axios` (for CCTV API client)
  - `echarts` & `echarts-for-react` (for CCTV charts)
  - `lucide-react` (for icons across landing page and CCTV views)
- [ ] Verify `npm run build` passes with new packages.

### Phase 3: Porting CCTV Types, Context & Services
- [ ] Copy and organize types into `c:/PJT/frontend/src/types/cctv.ts` or `src/features/cctv/types`.
- [ ] Configure `cctvApi.ts` in `src/services/` with environment fallback (`VITE_CCTV_API_URL` or `/cctv-api`).
- [ ] Implement `AppContext.tsx` in `c:/PJT/frontend/src/features/cctv/context/AppContext.tsx`.

### Phase 4: Porting & Theming CCTV Views to Skill Analysis Design
- [ ] Port common components: `MetricCard`, `CovenantBadge`, `DataTable`, `ErrorBoundary`.
- [ ] Re-theme components from dark mode (`bg-slate-950`) to Skill Analysis light mode (`bg-white`, `border-gray-200`, `text-gray-900`, `text-blue-600` accents).
- [ ] Port chart components: `PsiGaugeChart`, `RadialGaugeChart`, `SankeyChart`, `StackedBarChart`, `TrendVarianceChart`, `BarChart`. Re-theme chart options for light backgrounds.
- [ ] Port CCTV video components: `LiveVideoPlayer`, `VideoUploadModal`.
- [ ] Port 11 views into `c:/PJT/frontend/src/features/cctv/pages/`:
  - `View01LiveCctv.tsx`
  - `View02TrackDetails.tsx`
  - `View03WorkflowEfficiency.tsx`
  - `View04ActivityDistribution.tsx`
  - `View05OccupancyPresence.tsx`
  - `View06OutputEffectiveness.tsx`
  - `View07TeamWorkspace.tsx`
  - `View08HistoricalComparison.tsx`
  - `View09VideoExport.tsx`
  - `View10DataQuality.tsx`
  - `ZoneEditor.tsx`

### Phase 5: Build Flagship First-Load Landing Page (`/`)
- [ ] Create `c:/PJT/frontend/src/routes/LandingPage.tsx`:
  - Hero section with platform branding ("Unified Intelligence Platform").
  - Two prominent interactive product cards:
    - **CCTV Analytics:** Operational intelligence, occupancy, workflow bottlenecks, activity analytics. Action: "Launch CCTV Analytics" $\to$ `/cctv`.
    - **Skill Analysis:** Meeting behavioral analysis, speech, prosody, participant interaction, and NTS reports. Action: "Launch Skill Analysis" $\to$ `/dashboard` (or `/login`).
  - System service health indicators.
  - Features overview and keyboard accessibility.

### Phase 6: Unified Router & Layout Integration
- [ ] Create `CctvLayout.tsx` matching Skill Analysis styling with a top navigation bar (including "Home" button to return to `/`) and clean sidebar.
- [ ] Update `c:/PJT/frontend/src/App.tsx` to mount:
  - `/` $\to$ `LandingPage`
  - `/cctv/*` $\to$ `CctvLayout` with nested CCTV view routes.
  - `/dashboard`, `/projects/...`, `/meetings/...` $\to$ Skill Analysis views.
- [ ] Update Skill Analysis header (`ProtectedLayout.tsx`) with a "Platform Home" link back to `/`.

### Phase 7: Vite Proxy & Port Configuration
- [ ] Update `c:/PJT/frontend/vite.config.ts` to proxy:
  - Skill Analysis backend: `http://127.0.0.1:8000`
  - CCTV backend: `http://127.0.0.1:8001`
- [ ] Provide startup script / configuration for CCTV FastAPI backend on port 8001.

### Phase 8: Testing & Verification
- [ ] Build verification: `npm run build` in `c:/PJT/frontend` with 0 TypeScript/Vite errors.
- [ ] Route testing: verify landing page, CCTV views, and Skill Analysis views.
- [ ] Create `TEST_RESULTS.md`.
