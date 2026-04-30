import { request } from "../request";
import { buildAuthHeaders } from "../authHeaders";

export interface MySkill {
  skill_name: string;
  source: string;
  description: string;
  version: string | null;
  received_version: string | null;
  distributed_by: string | null;
  is_received: boolean;
  has_update: boolean;
  category?: string;
  creator_name?: string;
}

export interface FileTreeNode {
  name: string;
  type: "file" | "directory";
  path: string;
  children?: FileTreeNode[];
}

export interface FileContentResponse {
  content: string;
  file_type: string;
}

function mergeHeaders(extra?: Record<string, string>): RequestInit {
  const base = buildAuthHeaders();
  const merged: Record<string, string> = { ...base, ...(extra || {}) };
  return { headers: new Headers(merged) };
}

export const mySkillsApi = {
  getCreatedSkills: async (
    sourceId: string,
    userId: string
  ): Promise<MySkill[]> => {
    const opts = mergeHeaders({
      "X-Source-Id": sourceId,
      "X-User-Id": userId,
    });
    const all = await request<MySkill[]>("/market/skills/mine", opts);
    return all.filter((s) => !s.is_received);
  },

  getReceivedSkills: async (
    sourceId: string,
    userId: string
  ): Promise<MySkill[]> => {
    const opts = mergeHeaders({
      "X-Source-Id": sourceId,
      "X-User-Id": userId,
    });
    const all = await request<MySkill[]>("/market/skills/received", opts);
    return all.filter((s) => s.is_received);
  },

  listSkillFiles: async (
    sourceId: string,
    userId: string,
    userName: string,
    bbkId: string,
    skillName: string
  ): Promise<FileTreeNode[]> => {
    const opts = mergeHeaders({
      "X-Source-Id": sourceId,
      "X-User-Id": userId,
      "X-User-Name": encodeURIComponent(userName),
      "X-Bbk-Id": bbkId,
    });
    return request<FileTreeNode[]>(
      `/market/skills/mine/${skillName}/files`,
      opts
    );
  },

  readSkillFile: async (
    sourceId: string,
    userId: string,
    userName: string,
    bbkId: string,
    skillName: string,
    filePath: string
  ): Promise<FileContentResponse> => {
    const opts = mergeHeaders({
      "X-Source-Id": sourceId,
      "X-User-Id": userId,
      "X-User-Name": encodeURIComponent(userName),
      "X-Bbk-Id": bbkId,
    });
    return request<FileContentResponse>(
      `/market/skills/mine/${skillName}/files/${filePath}`,
      opts
    );
  },

  saveSkillFile: async (
    sourceId: string,
    userId: string,
    userName: string,
    bbkId: string,
    skillName: string,
    filePath: string,
    content: string
  ): Promise<void> => {
    const opts: RequestInit = {
      method: "PUT",
      headers: new Headers({
        "Content-Type": "application/json",
        "X-Source-Id": sourceId,
        "X-User-Id": userId,
        "X-User-Name": encodeURIComponent(userName),
        "X-Bbk-Id": bbkId,
      }),
      body: JSON.stringify({ content }),
    };
    await request<void>(`/market/skills/mine/${skillName}/files/${filePath}`, opts);
  },

  deleteSkill: async (
    sourceId: string,
    userId: string,
    userName: string,
    bbkId: string,
    skillName: string
  ): Promise<void> => {
    const opts: RequestInit = {
      method: "DELETE",
      headers: new Headers({
        "X-Source-Id": sourceId,
        "X-User-Id": userId,
        "X-User-Name": encodeURIComponent(userName),
        "X-Bbk-Id": bbkId,
      }),
    };
    await request<void>(`/market/skills/mine/${skillName}`, opts);
  },
};
