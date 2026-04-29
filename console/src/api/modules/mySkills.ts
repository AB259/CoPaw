import { request } from "../request";

export interface MySkill {
  skill_name: string;
  source: string;
  description: string;
  version: string | null;
  received_version: string | null;
  distributed_by: string | null;
  is_received: boolean;
  has_update: boolean;
}

function getHeaders(extra?: Record<string, string>): RequestInit {
  const headers: Record<string, string> = extra || {};
  return { headers: new Headers(headers) };
}

export const mySkillsApi = {
  getCreatedSkills: async (
    sourceId: string,
    userId: string
  ): Promise<MySkill[]> => {
    const opts = getHeaders({
      "X-Source-Id": sourceId,
      "X-User-Id": userId,
    });
    const all = await request<MySkill[]>("/api/skills/mine", opts);
    return all.filter((s) => !s.is_received);
  },

  getReceivedSkills: async (
    sourceId: string,
    userId: string
  ): Promise<MySkill[]> => {
    const opts = getHeaders({
      "X-Source-Id": sourceId,
      "X-User-Id": userId,
    });
    const all = await request<MySkill[]>("/api/skills/received", opts);
    return all.filter((s) => s.is_received);
  },
};
