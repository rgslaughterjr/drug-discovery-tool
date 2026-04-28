import axios, { AxiosInstance } from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class ApiClient {
  private client: AxiosInstance;
  private sessionId: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      timeout: 30000,
    });

    this.client.interceptors.request.use((config) => {
      if (this.sessionId) {
        config.headers['X-Session-ID'] = this.sessionId;
      }
      return config;
    });

    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          this.sessionId = null;
          window.location.href = '/';
        }
        return Promise.reject(error);
      }
    );
  }

  setSessionId(sessionId: string | null) {
    this.sessionId = sessionId;
  }

  async createSession(provider: string, apiKey: string, model: string) {
    const response = await this.client.post('/session/create', {
      provider,
      api_key: apiKey,
      model,
    });
    return response.data;
  }

  async deleteSession(sessionId: string) {
    const response = await this.client.delete(`/session/${sessionId}`);
    return response.data;
  }

  async getAvailableModels() {
    const response = await this.client.get('/api/models/available');
    return response.data;
  }

  async evaluateTarget(organism: string, proteinName: string, proteinId?: string) {
    const response = await this.client.post('/api/workflow/evaluate-target', {
      organism,
      protein_name: proteinName,
      protein_id: proteinId,
    });
    return response.data;
  }

  async getControls(organism: string, proteinName: string, pdbId: string) {
    const response = await this.client.post('/api/workflow/get-controls', {
      organism,
      protein_name: proteinName,
      pdb_id: pdbId,
    });
    return response.data;
  }

  async prepScreening(
    organism: string,
    proteinName: string,
    pdbId: string,
    mechanism: string,
    dockingSoftware?: string
  ) {
    const response = await this.client.post('/api/workflow/prep-screening', {
      organism,
      protein_name: proteinName,
      pdb_id: pdbId,
      mechanism,
      docking_software: dockingSoftware,
    });
    return response.data;
  }

  async analyzeHits(
    proteinName: string,
    numCompounds: number,
    dockingScoresSummary: string,
    positiveControlsAffinity?: string
  ) {
    const response = await this.client.post('/api/workflow/analyze-hits', {
      protein_name: proteinName,
      num_compounds: numCompounds,
      docking_scores_summary: dockingScoresSummary,
      positive_controls_affinity: positiveControlsAffinity,
    });
    return response.data;
  }

  // ------ New agentic endpoints ------

  async listResearchSessions() {
    const response = await this.client.get('/api/agent/research-sessions');
    return response.data;
  }

  async createResearchSession(name?: string) {
    const response = await this.client.post('/api/agent/research-sessions', { name });
    return response.data;
  }

  async deleteResearchSession(rsId: string) {
    const response = await this.client.delete(`/api/agent/research-sessions/${rsId}`);
    return response.data;
  }

  async exportCompoundsCsv(rsId: string): Promise<Blob> {
    const response = await this.client.get(`/api/export/${rsId}/compounds.csv`, {
      responseType: 'blob',
    });
    return response.data as Blob;
  }

  async exportResultsJson(rsId: string) {
    const response = await this.client.get(`/api/export/${rsId}/results.json`);
    return response.data;
  }
}

export const apiClient = new ApiClient();
