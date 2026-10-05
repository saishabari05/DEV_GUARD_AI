import React, { useState } from 'react';
import {
  investigate,
  approveFix,
  importGitRepo,
  uploadZipRepo,
  getPatchUrl,
  getDownloadFixedRepoUrl,
} from '../api/devguard';

const Header = ({ status, provider }) => (
  <header className="header">
    <div className="header-title" style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
      DEVGUARD AI
      <span className="status-badge" style={{ backgroundColor: '#2d3748', fontSize: '11px', color: '#edf2f7' }}>
        AI Provider: <strong style={{ color: provider === 'gemini' ? '#48bb78' : '#e2e8f0', marginLeft: '4px' }}>{provider ? provider.toUpperCase() : 'MOCK'}</strong>
      </span>
    </div>
    <div className="status-badge">
      <div className="status-dot" style={{ backgroundColor: status === 'Ready' ? 'var(--success)' : 'var(--accent)' }}></div>
      System {status}
    </div>
  </header>
);

const DiffViewer = ({ diff }) => {
  if (!diff) return <div className="code-block">No diff available.</div>;
  const lines = diff.split('\n');
  return (
    <div className="code-block">
      {lines.map((line, i) => {
        let className = '';
        if (line.startsWith('+') && !line.startsWith('+++')) className = 'diff-addition';
        if (line.startsWith('-') && !line.startsWith('---')) className = 'diff-removal';
        return <span key={i} className={className}>{line + '\n'}</span>;
      })}
    </div>
  );
};

export default function Dashboard() {
  const [sourceType, setSourceType] = useState('git'); // git, zip
  const [gitUrl, setGitUrl] = useState('');
  const [selectedZip, setSelectedZip] = useState(null);
  
  const [mode, setMode] = useState('autonomous'); // autonomous, directed
  const [activeRepoId, setActiveRepoId] = useState('');
  const [repoMetadata, setRepoMetadata] = useState(null);
  const [ingestLoading, setIngestLoading] = useState(false);

  const [bugReport, setBugReport] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const [investigation, setInvestigation] = useState(null);
  const [timelineState, setTimelineState] = useState('IDLE');
  const [approvalState, setApprovalState] = useState('IDLE');

  const handleIngestRepo = async () => {
    setError('');
    setIngestLoading(true);
    try {
      if (sourceType === 'git') {
        if (!gitUrl) throw new Error('Please enter a valid Git URL.');
        const res = await importGitRepo(gitUrl);
        setActiveRepoId(res.workspace_id);
        setRepoMetadata(res.metadata);
      } else if (sourceType === 'zip') {
        if (!selectedZip) throw new Error('Please select a ZIP file to upload.');
        const res = await uploadZipRepo(selectedZip);
        setActiveRepoId(res.workspace_id);
        setRepoMetadata(res.metadata);
      }
    } catch (err) {
      setError(getApiErrorMessage(err, 'Failed to ingest repository.'));
    } finally {
      setIngestLoading(false);
    }
  };


  const handleInvestigate = async () => {
    if (loading) return;
    if (!activeRepoId) {
      setError('Repository selection is required.');
      return;
    }
    if (mode === 'directed' && !bugReport.trim()) {
      setError('Bug report is required for Directed Investigation.');
      return;
    }
    setError('');
    setLoading(true);
    setTimelineState('INVESTIGATING');
    setInvestigation(null);
    setApprovalState('IDLE');

    try {
      const result = await investigate(activeRepoId, mode === 'directed' ? bugReport : null, true, mode);
      setInvestigation(result);
      if (result.success || result.status) {
        setTimelineState('DONE');
      } else {
        setTimelineState('FAILED');
        setError(result.error || result.message || 'Investigation failed.');
      }
    } catch (err) {
      setError(getApiErrorMessage(err, 'Unable to connect to backend.'));
      setTimelineState('FAILED');
    } finally {
      setLoading(false);
    }
  };

  const handleApproveAndValidate = async () => {
    const patchToValidate = investigation?.proposed_patch || (
      investigation?.patch && investigation?.affected_file ? 
      { file: investigation.affected_file, patch: investigation.patch, description: investigation.proposed_fix } : null
    );

    if (!patchToValidate) return;
    setError('');
    setApprovalState('APPROVING');
    try {
      const res = await approveFix(activeRepoId, patchToValidate);
      setInvestigation((prev) => ({
        ...prev,
        status: res.status,
        validation_pipeline: res.validation_pipeline,
      }));
      setApprovalState('DONE');
    } catch (err) {
      setError('Failed to approve fix and run validation.');
      setApprovalState('FAILED');
    }
  };

  const handleDownloadReport = () => {
    if (!investigation?.report_markdown) return;
    const blob = new Blob([investigation.report_markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `devguard_report_${activeRepoId}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const currentProvider = investigation?.provider || 'mock';

  return (
    <div className="dashboard-container">
      <Header status={loading ? 'Investigating...' : 'Ready'} provider={currentProvider} />
      <div className="main-content">
        <aside className="sidebar">
          <div>
            <div className="panel-title">Repository Source</div>
            <div className="input-group" style={{ flexDirection: 'row', gap: '8px', marginBottom: '12px' }}>
              <label style={{ fontSize: '13px', cursor: 'pointer' }}>
                <input type="radio" value="git" checked={sourceType === 'git'} onChange={() => setSourceType('git')} /> Git URL
              </label>
              <label style={{ fontSize: '13px', cursor: 'pointer' }}>
                <input type="radio" value="zip" checked={sourceType === 'zip'} onChange={() => setSourceType('zip')} /> ZIP Upload
              </label>
            </div>

            {sourceType === 'git' && (
              <div className="input-group">
                <input
                  type="text"
                  placeholder="https://github.com/owner/repo.git"
                  value={gitUrl}
                  onChange={(e) => setGitUrl(e.target.value)}
                  disabled={ingestLoading || loading}
                />
                <button className="primary" onClick={handleIngestRepo} disabled={ingestLoading || loading}>
                  {ingestLoading ? 'Cloning...' : 'Import Git Repository'}
                </button>
              </div>
            )}

            {sourceType === 'zip' && (
              <div className="input-group">
                <input
                  type="file"
                  accept=".zip"
                  onChange={(e) => setSelectedZip(e.target.files[0])}
                  disabled={ingestLoading || loading}
                />
                <button className="primary" onClick={handleIngestRepo} disabled={ingestLoading || loading || !selectedZip}>
                  {ingestLoading ? 'Extracting...' : 'Upload Repository ZIP'}
                </button>
              </div>
            )}

          </div>

          {repoMetadata && (
            <div>
              <div className="panel-title">Repository Metadata</div>
              <div className="info-grid" style={{ fontSize: '12px' }}>
                <div className="info-label">Language</div>
                <div>{repoMetadata.language}</div>
                <div className="info-label">Framework</div>
                <div>{repoMetadata.framework}</div>
                <div className="info-label">Test Command</div>
                <div><code>{repoMetadata.test_command}</code></div>
                <div className="info-label">File Count</div>
                <div>{repoMetadata.file_count} files</div>
              </div>
            </div>
          )}

          <div>
            <div className="panel-title">Investigation Mode</div>
            <div className="input-group" style={{ flexDirection: 'row', gap: '12px', marginBottom: '12px' }}>
              <label style={{ fontSize: '13px', cursor: 'pointer' }}>
                <input type="radio" value="directed" checked={mode === 'directed'} onChange={() => setMode('directed')} /> Directed Investigation
              </label>
              <label style={{ fontSize: '13px', cursor: 'pointer' }}>
                <input type="radio" value="autonomous" checked={mode === 'autonomous'} onChange={() => setMode('autonomous')} /> Autonomous Discovery
              </label>
            </div>
          </div>

          {mode === 'directed' && (
            <div>
              <div className="panel-title">Bug Report</div>
              <div className="input-group">
                <textarea 
                  value={bugReport} 
                  onChange={(e) => setBugReport(e.target.value)}
                  placeholder="Describe the problem experienced..."
                  disabled={loading}
                />
              </div>
            </div>
          )}

          <div style={{ marginTop: '8px' }}>
            <button className="primary" onClick={handleInvestigate} disabled={loading} style={{ width: '100%' }}>
              {loading ? 'Investigating...' : (mode === 'directed' ? 'Start Directed Investigation' : 'Run Autonomous Discovery')}
            </button>
          </div>

          <div style={{ marginTop: '16px' }}>
            <div className="panel-title">Investigation Timeline</div>
            <div className="timeline">
              {(() => {
                const hasEvidence = Array.isArray(investigation?.evidence)
                  ? investigation.evidence.length > 0
                  : Array.isArray(investigation?.root_cause?.evidence) && investigation.root_cause.evidence.length > 0;
                const hasRootCause =
                  investigation &&
                  investigation.confidence !== 'INSUFFICIENT' &&
                  (investigation.affected_file || investigation.root_cause?.file) &&
                  (investigation.affected_file || investigation.root_cause?.file) !== 'N/A';
                const hasPatch = Boolean(investigation?.proposed_patch || investigation?.patch);
                const isInvestigating = timelineState === 'INVESTIGATING';
                const steps = [
                  ['PROJECT_DETECTED', Boolean(activeRepoId), 'Repository imported'],
                  ['EVIDENCE_COLLECTED', hasEvidence, hasEvidence ? 'Repository evidence collected' : 'Evidence not yet sufficient'],
                  ['ROOT_CAUSE_IDENTIFIED', hasRootCause, hasRootCause ? 'Evidence-backed root cause identified' : 'Root cause not identified'],
                  ['PATCH_PROPOSED', hasPatch, hasPatch ? 'Patch proposed' : 'No patch proposed'],
                  ['AWAITING_VALIDATION', Boolean(hasPatch && investigation?.status !== 'PASSED'), hasPatch ? 'Awaiting user approval / validation' : 'Validation skipped'],
                ];
                return steps.map(([label, complete, detail]) => (
                  <div key={label} className={`timeline-item ${complete ? 'completed' : isInvestigating ? 'current' : 'pending'}`}>
                    {complete ? '✓' : isInvestigating ? '●' : '○'} {label}
                    <span style={{ marginLeft: '8px', opacity: 0.65, fontSize: '11px' }}>{detail}</span>
                  </div>
                ));
              })()}
            </div>
          </div>
        </aside>

        <main className="workspace">
          {error && <div className="error-banner">{error}</div>}
          
          {!investigation && !loading && (
            <div className="card">
              <div className="card-header">Welcome to DEVGUARD AI</div>
              <p>Select a repository and launch an evidence-first investigation or autonomous discovery.</p>
            </div>
          )}

          {investigation && (
            <>
              {investigation.provider_note && (
                <div className="card" style={{ borderColor: 'var(--accent)', backgroundColor: 'rgba(96, 165, 250, 0.05)' }}>
                  <div style={{ fontSize: '12px', color: 'var(--accent)', fontWeight: 'bold' }}>
                    ℹ {investigation.provider_note} (Provider: {currentProvider.toUpperCase()})
                  </div>
                </div>
              )}

              <div className="card">
                <div className="card-header">Evidence</div>
                {(investigation.evidence || investigation.root_cause?.evidence)?.length > 0 ? (
                  <div className="code-block">
                    {(investigation.evidence || investigation.root_cause.evidence).map((ev, i) => (
                      <div key={i}>
                        - <strong>[{ev.type ? ev.type.toUpperCase() : 'EVIDENCE'}] {ev.source || ev.file || 'Source'}</strong>: {ev.description || ev.observation}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p style={{ color: 'var(--danger)' }}>Insufficient evidence gathered from repository.</p>
                )}
              </div>

              <div className="card">
                <div className="card-header">Root Cause Analysis</div>
                <div className="info-grid">
                  <div className="info-label">Affected File</div>
                  <div><code>{investigation.affected_file || investigation.root_cause?.file || 'N/A'}</code></div>
                  <div className="info-label">Affected Function</div>
                  <div><code>{investigation.affected_function || investigation.root_cause?.function || 'N/A'}</code></div>
                  <div className="info-label">Root Cause Summary</div>
                  <div>{investigation.root_cause?.summary || investigation.bug_summary || 'N/A'}</div>
                  <div className="info-label">Confidence</div>
                  <div><strong>{investigation.confidence || investigation.root_cause?.confidence || 'INSUFFICIENT'}</strong></div>
                </div>
              </div>

              {(investigation.proposed_patch || investigation.patch) ? (
                <div className="card">
                  <div className="card-header">Proposed Fix & Diff Preview</div>
                  <div className="info-grid" style={{ marginBottom: '16px' }}>
                    <div className="info-label">Target File</div>
                    <div><code>{investigation.proposed_patch?.file || investigation.affected_file}</code></div>
                    <div className="info-label">Explanation</div>
                    <div>{investigation.proposed_patch?.description || investigation.proposed_fix || 'Patch proposed to resolve issue.'}</div>
                  </div>
                  
                  {(investigation.diff_preview || investigation.patch) && (
                    <>
                      <div className="panel-title">Unified Diff</div>
                      <DiffViewer diff={investigation.diff_preview || investigation.patch} />
                    </>
                  )}
                  
                  <div className="button-group" style={{ marginTop: '16px' }}>
                    <button 
                      className="primary" 
                      onClick={handleApproveAndValidate}
                      disabled={approvalState === 'APPROVING' || investigation.status === 'PASSED'}
                    >
                      {approvalState === 'APPROVING' ? 'Applying & Validating Fix...' : (investigation.status === 'PASSED' ? 'Fix Approved & Validated' : 'Approve & Validate Fix')}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="card">
                  <div className="card-header">Proposed Patch</div>
                  <p>Patch is not available for this investigation result.</p>
                </div>
              )}

              {/* Show actual pre/post test validation execution results */}
              {investigation.validation_pipeline && (
                <div className="card">
                  <div className="card-header">Validation Results</div>
                  <div className="validation-panel">
                    <div>
                      <div className="panel-title">BEFORE FIX</div>
                      <div className="code-block" style={{ color: investigation.validation_pipeline.pre_test?.exit_code === 0 ? 'var(--success)' : 'var(--danger)' }}>
                        Command: {investigation.validation_pipeline.pre_test?.command || 'N/A'}{'\n'}
                        Exit Code: {investigation.validation_pipeline.pre_test?.exit_code ?? 'N/A'}{'\n\n'}
                        {investigation.validation_pipeline.pre_test?.stdout || investigation.validation_pipeline.pre_test?.stderr}
                      </div>
                    </div>
                    <div>
                      <div className="panel-title">AFTER FIX</div>
                      {investigation.validation_pipeline.post_test ? (
                        <div className="code-block" style={{ color: investigation.validation_pipeline.post_test.exit_code === 0 ? 'var(--success)' : 'var(--danger)' }}>
                          Command: {investigation.validation_pipeline.post_test.command}{'\n'}
                          Exit Code: {investigation.validation_pipeline.post_test.exit_code}{'\n\n'}
                          {investigation.validation_pipeline.post_test.stdout || investigation.validation_pipeline.post_test.stderr}
                        </div>
                      ) : (
                        <div className="code-block" style={{ color: 'var(--text-muted)' }}>
                          NOT_VALIDATED (Post-fix test execution has not run or failed prior step)
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Fix Delivery Section */}
              {investigation.status === 'PASSED' && (
                <div className="card" style={{ borderColor: 'var(--success)' }}>
                  <div className="card-header" style={{ color: 'var(--success)' }}>Fix Delivery — VERIFIED</div>
                  <p>The fix was validated successfully by executing post-patch tests.</p>
                  <div className="button-group" style={{ marginTop: '16px' }}>
                    <a href={getPatchUrl(activeRepoId)} className="button primary" download style={{ textDecoration: 'none' }}>
                      Download Patch (.patch)
                    </a>
                    <a href={getDownloadFixedRepoUrl(activeRepoId)} className="button primary" download style={{ textDecoration: 'none', backgroundColor: '#38a169' }}>
                      Download Fixed Repository (.zip)
                    </a>
                  </div>
                </div>
              )}

              {investigation.report_markdown && (
                <div className="card">
                  <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span>Investigation Report</span>
                    <button className="primary" onClick={handleDownloadReport} style={{ padding: '6px 12px', fontSize: '12px' }}>
                      Download Report (.md)
                    </button>
                  </div>
                  <pre className="code-block" style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>
                    {investigation.report_markdown}
                  </pre>
                </div>
              )}

              {investigation.status && (
                <div className="card">
                  <div className="card-header">Investigation Summary</div>
                  <div className="info-grid">
                    <div className="info-label">Final Status</div>
                    <div style={{ color: investigation.status === 'PASSED' ? 'var(--success)' : 'var(--accent)' }}>
                      {investigation.status === 'PASSED' ? '✓ PASSED' : investigation.status}
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}

