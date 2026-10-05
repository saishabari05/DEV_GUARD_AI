import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getApiErrorMessage = (err, fallback = 'Request failed.') =>
  err?.response?.data?.error ||
  err?.response?.data?.message ||
  err?.message ||
  fallback;

export const importGitRepo = async (gitUrl) => {
  const response = await api.post('/repositories/import', { git_url: gitUrl });
  return response.data;
};

export const uploadZipRepo = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/repositories/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const investigate = async (repository, bugReport, requireApproval = true, mode = 'directed') => {
  const response = await api.post('/investigate', {
    repository,
    bug_report: bugReport,
    require_approval: requireApproval,
    mode
  });
  return response.data;
};


export const approveFix = async (repository, proposedPatch) => {
  const response = await api.post('/fix/approve', {
    repository,
    proposed_patch: proposedPatch,
  });
  return response.data;
};

export const applyFix = async (repository, filePath, patch) => {
  const response = await api.post('/tools/apply', {
    repository,
    file_path: filePath,
    patch,
  });
  return response.data;
};

export const revertFix = async (repository, filePath) => {
  const response = await api.post('/tools/revert', {
    repository,
    file_path: filePath,
  });
  return response.data;
};

export const runTests = async (repository) => {
  const response = await api.post('/tools/test', {
    repository,
  });
  return response.data;
};

export const getPatchUrl = (repoId) => `${API_BASE_URL}/investigations/${repoId}/patch`;
export const getDownloadFixedRepoUrl = (repoId) => `${API_BASE_URL}/investigations/${repoId}/download`;
