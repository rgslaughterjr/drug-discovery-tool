import React, { useState } from 'react';
import './CompoundTable.css';

interface Compound {
  rank?: number;
  name?: string;
  compound_type?: string;
  pubchem_cid?: number;
  chembl_id?: string;
  smiles?: string;
  mw?: number;
  logp?: number;
  tpsa?: number;
  hbd?: number;
  hba?: number;
  activity_value_nm?: number;
  activity_nm?: number;
  activity_type?: string;
  is_pains?: boolean;
  docking_score?: number;
  notes?: string;
}

interface Props {
  compounds: Compound[];
  title?: string;
}

type SortKey = keyof Compound;

export function CompoundTable({ compounds, title }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>('rank');
  const [sortAsc, setSortAsc] = useState(true);

  if (!compounds || compounds.length === 0) return null;

  const sorted = [...compounds].sort((a, b) => {
    const av = a[sortKey] as number | string | undefined ?? '';
    const bv = b[sortKey] as number | string | undefined ?? '';
    if (av < bv) return sortAsc ? -1 : 1;
    if (av > bv) return sortAsc ? 1 : -1;
    return 0;
  });

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc((v) => !v);
    else { setSortKey(key); setSortAsc(true); }
  };

  const cols: { key: SortKey; label: string }[] = [
    { key: 'rank', label: '#' },
    { key: 'name', label: 'Name' },
    { key: 'smiles', label: 'SMILES' },
    { key: 'mw', label: 'MW' },
    { key: 'logp', label: 'logP' },
    { key: 'activity_value_nm', label: 'Activity (nM)' },
    { key: 'is_pains', label: 'PAINS' },
    { key: 'docking_score', label: 'Score' },
  ];

  return (
    <div className="compound-table-wrapper">
      {title && <h4 className="compound-table-title">{title}</h4>}
      <div className="compound-table-scroll">
        <table className="compound-table">
          <thead>
            <tr>
              {cols.map((c) => (
                <th key={c.key} onClick={() => toggleSort(c.key)} className="sortable">
                  {c.label}
                  {sortKey === c.key ? (sortAsc ? ' ▲' : ' ▼') : ''}
                </th>
              ))}
              <th>Links</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((row, i) => {
              const activityNm = row.activity_value_nm ?? row.activity_nm;
              return (
                <tr key={i} className={row.is_pains ? 'pains-row' : ''}>
                  <td>{row.rank ?? i + 1}</td>
                  <td className="name-cell" title={row.name}>{row.name ?? '—'}</td>
                  <td className="smiles-cell">
                    <span className="smiles-text" title={row.smiles}>{row.smiles ? row.smiles.slice(0, 30) + (row.smiles.length > 30 ? '…' : '') : '—'}</span>
                    {row.smiles && (
                      <button
                        className="copy-btn"
                        onClick={() => navigator.clipboard.writeText(row.smiles!)}
                        title="Copy SMILES"
                      >⎘</button>
                    )}
                  </td>
                  <td>{row.mw ? row.mw.toFixed(1) : '—'}</td>
                  <td>{row.logp != null ? row.logp.toFixed(2) : '—'}</td>
                  <td className={activityNm != null && activityNm < 100 ? 'good-activity' : ''}>
                    {activityNm != null ? activityNm.toFixed(1) : '—'}
                    {activityNm != null && row.activity_type ? ` ${row.activity_type}` : ''}
                  </td>
                  <td className={row.is_pains ? 'pains-yes' : 'pains-no'}>
                    {row.is_pains == null ? '?' : row.is_pains ? '⚠ Yes' : 'No'}
                  </td>
                  <td>{row.docking_score != null ? row.docking_score.toFixed(2) : '—'}</td>
                  <td className="links-cell">
                    {row.pubchem_cid && (
                      <a
                        href={`https://pubchem.ncbi.nlm.nih.gov/compound/${row.pubchem_cid}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        title="View in PubChem"
                      >PubChem</a>
                    )}
                    {row.chembl_id && (
                      <a
                        href={`https://www.ebi.ac.uk/chembl/compound_report_card/${row.chembl_id}/`}
                        target="_blank"
                        rel="noopener noreferrer"
                        title="View in ChEMBL"
                      >ChEMBL</a>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="compound-count">{compounds.length} compound{compounds.length !== 1 ? 's' : ''}</p>
    </div>
  );
}
