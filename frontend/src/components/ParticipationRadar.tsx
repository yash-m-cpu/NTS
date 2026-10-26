import React from 'react';
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip
} from 'recharts';

interface ParticipationRadarProps {
  data: {
    track_label: string;
    dominance: number;
    participation: number;
    speech_ratio: number;
    listener_gaze: number;
  }[];
}

export const ParticipationRadar: React.FC<ParticipationRadarProps> = ({ data }) => {
  // We need to normalize or structure data for a Radar chart.
  // Radar expects data where each object is an AXIS (e.g. 'Dominance'),
  // and properties are the values for each track (e.g. 'Person 1': 0.8).
  
  if (!data || data.length === 0) return null;
  
  const axes = [
    { key: 'dominance', name: 'Dominance (Z)' },
    { key: 'participation', name: 'Participation (Z)' },
    { key: 'speech_ratio', name: 'Speech Time %' },
    { key: 'listener_gaze', name: 'Gaze on Speaker %' }
  ];
  
  const radarData = axes.map(axis => {
    const obj: any = { subject: axis.name, fullMark: 100 };
    data.forEach(track => {
      let val = (track as any)[axis.key];
      // Normalize Z-scores roughly to a 0-100 scale for visual comparison on the same radar
      if (axis.key === 'dominance' || axis.key === 'participation') {
          // Z score: typically -3 to 3. Map to 0-100 where 0 is 50.
          val = Math.max(0, Math.min(100, (val * 15) + 50)); 
      } else {
          // Percentages
          val = val * 100;
      }
      obj[track.track_label] = val;
    });
    return obj;
  });

  const colors = ["#8884d8", "#82ca9d", "#ffc658", "#ff7300", "#0088FE", "#00C49F"];

  return (
    <div className="w-full h-80 mt-4">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
          <PolarGrid />
          <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11 }} />
          <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} />
          <Tooltip />
          {data.map((track, i) => (
            <Radar
              key={track.track_label}
              name={track.track_label}
              dataKey={track.track_label}
              stroke={colors[i % colors.length]}
              fill={colors[i % colors.length]}
              fillOpacity={0.4}
            />
          ))}
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
};
