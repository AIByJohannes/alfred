import { fetchWithAuth } from "./client";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

export interface Job {
  id: string;
  userId: string;
  prompt: string;
  result: string;
  status: string;
  createdAt: string;
}

export const backendClient = {
  // Authentication
  async login(credentials: Record<string, string>) {
    return fetchWithAuth(`${BACKEND_URL}/auth/login`, {
      method: "POST",
      body: JSON.stringify(credentials),
    });
  },

  // Job History
  async getHistory(token: string): Promise<Job[]> {
    return fetchWithAuth(`${BACKEND_URL}/api/jobs/history`, {}, token);
  },
};
