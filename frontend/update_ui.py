with open('c:/PJT/frontend/src/routes/MeetingAnalysis.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

target = """          ) : <p className="text-gray-500">No speech data for this participant.</p>}
          <div className="bg-white p-4 border rounded">
            <h3 className="font-semibold mb-4">Speaking Ratio Comparison</h3>"""

replacement = """          ) : <p className="text-gray-500">No speech data for this participant.</p>}
          <div className="bg-white p-4 border rounded">
            <h3 className="font-semibold mb-2">Prosody & Voice Dynamics</h3>
            <p className="text-sm text-gray-500 mb-4">Pitch (F0) and Energy contours extracted natively via Praat/Parselmouth.</p>
            {(() => {
              const trackProsody = prosody.filter(p => p.participant_track_id === selectedTrackId);
              const trackMetrics = metrics.filter(m => m.participant_track_id === selectedTrackId);
              const medianF0 = trackMetrics.find(m => m.metric_key === 'pitch_p50_hz')?.value;
              const p10F0 = trackMetrics.find(m => m.metric_key === 'pitch_p10_hz')?.value;
              const p90F0 = trackMetrics.find(m => m.metric_key === 'pitch_p90_hz')?.value;
              return <ProsodyChart data={trackProsody} medianF0={medianF0} p10F0={p10F0} p90F0={p90F0} />
            })()}
          </div>
          <div className="bg-white p-4 border rounded">
            <h3 className="font-semibold mb-4">Speaking Ratio Comparison</h3>"""

if target in content:
    with open('c:/PJT/frontend/src/routes/MeetingAnalysis.tsx', 'w', encoding='utf-8') as f:
        f.write(content.replace(target, replacement))
    print('Replaced target 1')

target2 = """      return (
        <div className="space-y-6">
          <div className="bg-white p-4 border rounded">
            <h3 className="font-semibold mb-4">Interaction Graph</h3>"""

replacement2 = """      return (
        <div className="space-y-6">
          <div className="bg-white p-4 border rounded">
            <h3 className="font-semibold mb-2">Behavioral Radar</h3>
            <p className="text-sm text-gray-500 mb-4">Multi-modal traits comparing participant dominance and engagement.</p>
            {(() => {
              const radarData = tracks.map(track => {
                const trackMetrics = metrics.filter(m => m.participant_track_id === track.id);
                const getM = (k: string) => trackMetrics.find(m => m.metric_key === k)?.value || 0;
                return {
                  track_label: track.track_label,
                  dominance: getM('multimodal_dominance'),
                  participation: getM('multimodal_participation'),
                  speech_ratio: getM('speech_ratio'),
                  listener_gaze: getM('avg_listener_gaze_on_speaker_pct')
                };
              });
              return <ParticipationRadar data={radarData} />
            })()}
          </div>
          <div className="bg-white p-4 border rounded">
            <h3 className="font-semibold mb-4">Interaction Graph</h3>"""

if target2 in content:
    with open('c:/PJT/frontend/src/routes/MeetingAnalysis.tsx', 'w', encoding='utf-8') as f:
        # Read again to get updated content
        f.seek(0)
        content2 = f.read()
        f.write(content.replace(target, replacement).replace(target2, replacement2))
    print('Replaced target 2')
