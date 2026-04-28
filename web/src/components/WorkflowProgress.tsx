import React from 'react';
import './WorkflowProgress.css';

const STAGES = [
  { key: 'evaluate', label: 'Evaluate Target' },
  { key: 'controls', label: 'Generate Controls' },
  { key: 'screening', label: 'Prep Screening' },
  { key: 'hits', label: 'Analyze Hits' },
];

interface Props {
  currentStage: string | null;
}

export function WorkflowProgress({ currentStage }: Props) {
  const currentIdx = STAGES.findIndex((s) => s.key === currentStage);

  return (
    <div className="workflow-progress">
      {STAGES.map((stage, i) => {
        const done = i < currentIdx;
        const active = i === currentIdx;
        return (
          <React.Fragment key={stage.key}>
            <div className={`wf-step ${done ? 'done' : active ? 'active' : 'pending'}`}>
              <span className="wf-icon">{done ? '✓' : active ? '●' : '○'}</span>
              <span className="wf-label">{stage.label}</span>
            </div>
            {i < STAGES.length - 1 && (
              <div className={`wf-connector ${done ? 'done' : ''}`} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}
