import React from 'react';
import { ThinkingStep } from '../hooks/useAgentStream';
import './AgentThinking.css';

const TOOL_LABELS: Record<string, string> = {
  uniprot_search: 'UniProt',
  uniprot_entry_detail: 'UniProt',
  pdb_structure_search: 'RCSB PDB',
  pdb_binding_site_info: 'RCSB PDB',
  chembl_target_search: 'ChEMBL',
  chembl_bioactivity: 'ChEMBL',
  chembl_compound_detail: 'ChEMBL',
  pubchem_compound_lookup: 'PubChem',
  pubchem_bioactivity_search: 'PubChem',
  pubchem_similarity_search: 'PubChem',
  validate_smiles: 'RDKit',
  calculate_molecular_properties: 'RDKit',
  screen_pains: 'PAINS filter',
  compute_murcko_scaffolds: 'Murcko scaffolds',
  generate_decoys: 'Decoy generator',
  delegate_to_sub_agent: 'Sub-agent',
};

interface Props {
  steps: ThinkingStep[];
  currentAgent: string | null;
}

export function AgentThinking({ steps, currentAgent }: Props) {
  if (steps.length === 0 && !currentAgent) return null;

  return (
    <div className="agent-thinking">
      {currentAgent && (
        <div className="sub-agent-banner">
          <span className="pulse-dot" />
          Running <strong>{currentAgent.replace('_', ' ')}</strong> sub-agent (NVIDIA Nemotron)…
        </div>
      )}
      <div className="thinking-steps">
        {steps.map((step, i) => (
          <div key={i} className={`thinking-step ${step.status}`}>
            <span className="step-icon">{step.status === 'calling' ? '⟳' : '✓'}</span>
            <span className="step-db">{TOOL_LABELS[step.tool] ?? step.tool}</span>
            <span className="step-tool">{step.tool}</span>
            {step.duration_ms !== undefined && (
              <span className="step-duration">{step.duration_ms}ms</span>
            )}
            {step.summary && <StepSummary tool={step.tool} summary={step.summary} />}
          </div>
        ))}
      </div>
    </div>
  );
}

function StepSummary({ tool, summary }: { tool: string; summary: Record<string, unknown> }) {
  let text = '';
  if (tool.startsWith('uniprot')) {
    const top = summary.top as Record<string, unknown> | undefined;
    text = top ? `${top.gene_name ?? top.uniprot_id}` : summary.found ? 'Found' : 'Not found';
  } else if (tool.startsWith('pdb')) {
    text = summary.found
      ? `${summary.count ?? 1} structure(s), best: ${(summary.best as Record<string, unknown>)?.pdb_id ?? ''}`
      : 'No structures';
  } else if (tool.startsWith('chembl_bioactivity')) {
    text = summary.found ? `${summary.count} compounds, best: ${summary.best_nm} nM` : 'No data';
  } else if (tool.startsWith('chembl_target')) {
    const top = summary.top as Record<string, unknown> | undefined;
    text = top ? `${top.chembl_id}` : summary.found ? 'Found' : 'Not found';
  } else if (tool.startsWith('pubchem')) {
    text = summary.found ? `CID ${summary.cid}` : 'Not found';
  } else if (tool === 'validate_smiles') {
    text = summary.valid ? `MW ${summary.mw}, ${summary.ro5} Ro5 violations` : 'Invalid SMILES';
  } else if (tool === 'screen_pains') {
    text = `${summary.pains_count ?? 0} PAINS hits / ${summary.screened ?? 0} screened`;
  }
  if (!text) return null;
  return <span className="step-summary">{text}</span>;
}
