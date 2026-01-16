import { fetchWithAuth } from './client'

const AI_URL = process.env.NEXT_PUBLIC_AI_URL || 'http://localhost:8000'

export interface AIResponse {
  result: string
  job_id?: string
}

export const aiClient = {
  async runAgent(prompt: string, token: string): Promise<AIResponse> {
    return fetchWithAuth(
      `${AI_URL}/v1/agent/run`,
      {
        method: 'POST',
        body: JSON.stringify({ prompt }),
      },
      token,
    )
  },
}
