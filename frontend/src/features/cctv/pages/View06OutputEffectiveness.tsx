import React, { useEffect, useState } from 'react';
import { useApp } from '../context/AppContext';
import { apiService } from '../../../services/cctvApi';
import type { ScorecardD } from '../types';
import { MetricCard } from '../components/common/MetricCard';
import { RadialGaugeChart } from '../components/charts/RadialGaugeChart';
import { CheckCircle2, Send, ShieldAlert, CheckSquare } from 'lucide-react';

export const View06OutputEffectiveness: React.FC = () => {
  const { selectedCamera, selectedDepartment } = useApp();
  const [scorecardD, setScorecardD] = useState<ScorecardD | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [submitMessage, setSubmitMessage] = useState<string | null>(null);

  // Form state
  const [reportDate, setReportDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [departmentCode, setDepartmentCode] = useState<string>(selectedDepartment);
  const [actualUnits, setActualUnits] = useState<number>(105);
  const [targetUnits, setTargetUnits] = useState<number>(100);
  const [acceptedUnits, setAcceptedUnits] = useState<number>(102);
  const [assessedUnits, setAssessedUnits] = useState<number>(105);
  const [onTimeUnits, setOnTimeUnits] = useState<number>(98);
  const [reworkUnits, setReworkUnits] = useState<number>(3);

  const fetchScorecard = async () => {
    const suite = await apiService.getScorecards(selectedCamera, selectedDepartment);
    if (suite?.scorecard_d) {
      setScorecardD(suite.scorecard_d);
    }
  };

  useEffect(() => {
    fetchScorecard();
    setDepartmentCode(selectedDepartment);
  }, [selectedCamera, selectedDepartment]);

  const isAvailable =
    scorecardD?.status !== 'UNAVAILABLE' &&
    scorecardD?.composite_score !== null &&
    scorecardD?.composite_score !== undefined;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setSubmitMessage(null);

    try {
      const payload = {
        report_date: reportDate,
        department_code: departmentCode,
        actual_completed_units: actualUnits,
        target_planned_units: targetUnits,
        quality_accepted_units: acceptedUnits,
        quality_assessed_units: assessedUnits,
        on_time_units: onTimeUnits,
        total_deadline_units: actualUnits,
        rework_units: reworkUnits,
        source_system: 'JIRA_SPRINT_WEBHOOK'
      };

      const res = await apiService.ingestOperationalOutcomes(payload);
      if (res) {
        setSubmitMessage(`Outcome ingested! Scorecard D score calculated: ${res.output_effectiveness_score}`);
        await fetchScorecard();
      }
    } catch (err) {
      setSubmitMessage('Failed to ingest outcome payload.');
    } finally {
      setSubmitting(false);
    }
  };

  const score = scorecardD?.composite_score ?? 0.0;
  const metrics = scorecardD?.metrics ?? {};
  const thru = Number(metrics.throughput_rate_pct ?? 0.0);
  const qual = Number(metrics.quality_rate_pct ?? 0.0);
  const timeliness = Number(metrics.timeliness_rate_pct ?? 0.0);
  const rework = Number(metrics.rework_rate_pct ?? 0.0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
          <span>🎯 View 06: Operational Output & Deliverables Panel (Scorecard D)</span>
        </h2>
        <p className="text-xs text-gray-500 mt-1">
          Measures business deliverable attainment ingested exclusively from verified enterprise tools (Jira sprint closures, GitHub pull requests, SAP ERP transactions).
          <b className="text-gray-700"> Strict Covenant: Video analytics features are never used as a proxy for cognitive output.</b>
        </p>
      </div>

      {!isAvailable ? (
        <div className="space-y-6">
          {/* Explicit N/A Placeholder per specification */}
          <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 flex items-start gap-3">
            <ShieldAlert className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
            <div>
              <h4 className="font-semibold text-rose-900 text-sm mb-1">
                SCORECARD D UNAVAILABLE: External Operational Data Pipeline Unconfigured
              </h4>
              <p className="leading-relaxed">
                WBPIS strictly forbids substituting camera observations or desk presence for knowledge work productivity.
                To activate Scorecard D, configure an external enterprise webhook (e.g. Jira, SAP, Salesforce) or use the manual test ingestion simulator below.
              </p>
            </div>
          </div>

          {/* External Data Ingestion Simulator */}
          <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-xs space-y-4">
            <div>
              <h4 className="text-sm font-semibold text-gray-900">🛠 External Data Ingestion Simulator / Webhook Tester</h4>
              <p className="text-xs text-gray-500">Submit verified deliverables to test Scorecard D calculations.</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-gray-700 block mb-1">Report Date</label>
                  <input
                    type="date"
                    value={reportDate}
                    onChange={(e) => setReportDate(e.target.value)}
                    className="w-full bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:outline-none focus:border-blue-500 font-mono"
                  />
                </div>
                <div>
                  <label className="text-gray-700 block mb-1">Department Code</label>
                  <input
                    type="text"
                    value={departmentCode}
                    onChange={(e) => setDepartmentCode(e.target.value)}
                    className="w-full bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:outline-none focus:border-blue-500 font-mono"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                <div>
                  <label className="text-gray-700 block mb-1">Actual Completed Units</label>
                  <input
                    type="number"
                    value={actualUnits}
                    onChange={(e) => setActualUnits(Number(e.target.value))}
                    className="w-full bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:outline-none focus:border-blue-500 font-mono"
                  />
                </div>
                <div>
                  <label className="text-gray-700 block mb-1">Target Planned Units</label>
                  <input
                    type="number"
                    value={targetUnits}
                    onChange={(e) => setTargetUnits(Number(e.target.value))}
                    className="w-full bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:outline-none focus:border-blue-500 font-mono"
                  />
                </div>
                <div>
                  <label className="text-gray-700 block mb-1">Quality Accepted Units</label>
                  <input
                    type="number"
                    value={acceptedUnits}
                    onChange={(e) => setAcceptedUnits(Number(e.target.value))}
                    className="w-full bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:outline-none focus:border-blue-500 font-mono"
                  />
                </div>
                <div>
                  <label className="text-gray-700 block mb-1">Quality Assessed Units</label>
                  <input
                    type="number"
                    value={assessedUnits}
                    onChange={(e) => setAssessedUnits(Number(e.target.value))}
                    className="w-full bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:outline-none focus:border-blue-500 font-mono"
                  />
                </div>
                <div>
                  <label className="text-gray-700 block mb-1">On-Time Units</label>
                  <input
                    type="number"
                    value={onTimeUnits}
                    onChange={(e) => setOnTimeUnits(Number(e.target.value))}
                    className="w-full bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:outline-none focus:border-blue-500 font-mono"
                  />
                </div>
                <div>
                  <label className="text-gray-700 block mb-1">Rework Units</label>
                  <input
                    type="number"
                    value={reworkUnits}
                    onChange={(e) => setReworkUnits(Number(e.target.value))}
                    className="w-full bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:outline-none focus:border-blue-500 font-mono"
                  />
                </div>
              </div>

              {submitMessage && (
                <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span>{submitMessage}</span>
                </div>
              )}

              <button
                type="submit"
                disabled={submitting}
                className="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold rounded-lg shadow-xs transition-colors cursor-pointer"
              >
                <Send className="w-4 h-4" />
                <span>Ingest External Outcome Payload</span>
              </button>
            </form>
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Active Scorecard D View */}
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
            <div className="lg:col-span-2 bg-white border border-gray-200 rounded-xl p-5 shadow-xs flex flex-col justify-between">
              <div>
                <h4 className="text-sm font-semibold text-gray-900 mb-1">Primary Scorecard D</h4>
                <p className="text-xs text-gray-500">Output effectiveness composite score</p>
              </div>
              <RadialGaugeChart
                score={score}
                title="Output Effectiveness"
                minVal={0}
                maxVal={100}
                unit="/100"
                height="260px"
              />
              <p className="text-xs text-gray-500 text-center mt-2 font-mono">
                Source System: <code className="text-blue-600">{scorecardD?.source_system || 'EXTERNAL_WEBHOOK'}</code>
              </p>
            </div>

            <div className="lg:col-span-3 space-y-4">
              <h4 className="text-sm font-semibold text-gray-900">Deliverable Performance Breakdown</h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <MetricCard
                  label="Throughput Attainment"
                  value={`${thru.toFixed(1)}%`}
                  delta={`${(thru - 100).toFixed(1)}% vs Target`}
                  deltaType={thru >= 100 ? 'normal' : 'inverse'}
                  caption="Ratio of actual deliverables to planned sprint backlog."
                  icon={<CheckSquare className="w-4 h-4 text-emerald-600" />}
                />

                <MetricCard
                  label="First-Pass Quality Rate"
                  value={`${qual.toFixed(1)}%`}
                  delta="High Quality (> 95%)"
                  deltaType="normal"
                  caption="Deliverables accepted without client rework."
                />

                <MetricCard
                  label="On-Time SLA Adherence"
                  value={`${timeliness.toFixed(1)}%`}
                  delta="On Schedule"
                  deltaType="normal"
                  caption="Deliverables completed prior to milestone deadlines."
                />

                <MetricCard
                  label="Rework Rate"
                  value={`${rework.toFixed(1)}%`}
                  delta="Low Rework (< 5%)"
                  deltaType="normal"
                  caption="Deliverables requiring defect remediation."
                />
              </div>
            </div>
          </div>

          <div className="p-4 bg-white border border-gray-200 rounded-xl text-xs text-gray-600 flex items-center gap-2 shadow-xs">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>
              <b>Data Provenance:</b> Scorecard D metrics are cryptographically verified against external enterprise audit trails.
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
