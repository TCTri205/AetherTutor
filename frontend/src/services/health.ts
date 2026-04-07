import api from './api';

export interface HealthStatus {
  status: string;
  services: {
    postgres: boolean;
    redis: boolean;
    chromadb: boolean;
  };
  llm: {
    model: string;
    embedding_model: string;
    provider: 'openai' | 'ollama';
    mode: 'local' | 'cloud';
    healthy: boolean;
  };
}

export const healthService = {
  async checkHealth(): Promise<HealthStatus> {
    const response = await api.get<HealthStatus>('/health');
    return response.data;
  },
};
