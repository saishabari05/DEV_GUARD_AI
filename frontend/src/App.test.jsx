import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import Dashboard from './components/Dashboard';
import { investigate, applyFix, revertFix, runTests } from './api/devguard';

vi.mock('./api/devguard');

describe('Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('Dashboard renders successfully', () => {
    render(<Dashboard />);
    expect(screen.getByText('DEVGUARD AI')).toBeInTheDocument();
  });

  test('Repository selector and Bug report input work', () => {
    render(<Dashboard />);
    const repoSelect = screen.getByDisplayValue('auth_bug');
    expect(repoSelect).toBeInTheDocument();
    
    const bugInput = screen.getByPlaceholderText('Describe the problem the developer is experiencing...');
    expect(bugInput).toBeInTheDocument();
    
    fireEvent.change(bugInput, { target: { value: 'Test bug' } });
    expect(bugInput.value).toBe('Test bug');
  });

  test('Start Investigation calls API and shows loading state', async () => {
    investigate.mockResolvedValueOnce({
      success: true,
      root_cause: { summary: 'Mock root cause', evidence: [] },
      proposed_patch: { file: 'app/auth.py', description: 'Mock patch' }
    });

    render(<Dashboard />);
    const btn = screen.getByText('Start Investigation');
    fireEvent.click(btn);
    
    expect(btn).toHaveTextContent('Investigating...');
    expect(btn).toBeDisabled();
    
    await waitFor(() => {
      expect(investigate).toHaveBeenCalledWith('auth_bug', expect.any(String));
    });
  });

  test('Duplicate investigation requests are prevented', async () => {
    let resolveInvestigate;
    const promise = new Promise((resolve) => {
      resolveInvestigate = resolve;
    });
    investigate.mockReturnValue(promise);

    render(<Dashboard />);
    const btn = screen.getByText('Start Investigation');
    
    fireEvent.click(btn);
    expect(btn).toBeDisabled();
    
    fireEvent.click(btn);
    
    expect(investigate).toHaveBeenCalledTimes(1);
    
    resolveInvestigate({ success: true, root_cause: {} });
  });

  test('Investigation result renders properly', async () => {
    investigate.mockResolvedValueOnce({
      success: true,
      status: 'fix_accepted',
      root_cause: { summary: 'Mock root cause', file: 'mock.py', evidence: [] },
      proposed_patch: { file: 'mock.py', description: 'Mock patch', patch: 'mock patch' },
      validation_pipeline: {
        diff: '-old\n+new',
        pre_test: { status: 'failed', stdout: 'test failed' },
        post_test: { status: 'passed', stdout: 'test passed' }
      }
    });

    render(<Dashboard />);
    fireEvent.click(screen.getByText('Start Investigation'));
    
    await waitFor(() => {
      expect(screen.getByText('Mock root cause')).toBeInTheDocument();
      expect(screen.getByText('Mock patch')).toBeInTheDocument();
      expect(screen.getByText('-old')).toBeInTheDocument();
      expect(screen.getByText(/test failed/)).toBeInTheDocument();
      expect(screen.getByText(/test passed/)).toBeInTheDocument();
      expect(screen.getByText('✓ FIX VERIFIED')).toBeInTheDocument();
    });
  });

  test('Backend error renders', async () => {
    investigate.mockResolvedValueOnce({
      success: false,
      error: 'Backend exploded'
    });

    render(<Dashboard />);
    fireEvent.click(screen.getByText('Start Investigation'));
    
    await waitFor(() => {
      expect(screen.getByText('Backend exploded')).toBeInTheDocument();
    });
  });

  test('Apply Fix calls correct API', async () => {
    investigate.mockResolvedValueOnce({
      success: true,
      proposed_patch: { file: 'mock.py', description: 'Mock patch', patch: 'mock patch' }
    });
    applyFix.mockResolvedValueOnce({ success: true });
    runTests.mockResolvedValueOnce({ status: 'passed', stdout: 'manual pass' });

    render(<Dashboard />);
    fireEvent.click(screen.getByText('Start Investigation'));
    
    await waitFor(() => {
      expect(screen.getByText('Apply Fix')).toBeInTheDocument();
    });
    
    fireEvent.click(screen.getByText('Apply Fix'));
    
    await waitFor(() => {
      expect(screen.getByText(/manual pass/)).toBeInTheDocument();
    });
  });

  test('Revert Fix calls correct API', async () => {
    investigate.mockResolvedValueOnce({
      success: true,
      proposed_patch: { file: 'mock.py', description: 'Mock patch', patch: 'mock patch' }
    });
    revertFix.mockResolvedValueOnce({ success: true });
    runTests.mockResolvedValueOnce({ status: 'failed', stdout: 'manual fail' });

    render(<Dashboard />);
    fireEvent.click(screen.getByText('Start Investigation'));
    
    await waitFor(() => {
      expect(screen.getByText('Revert Fix')).toBeInTheDocument();
    });
    
    fireEvent.click(screen.getByText('Revert Fix'));
    
    await waitFor(() => {
      expect(screen.getByText(/manual fail/)).toBeInTheDocument();
    });
  });
});

