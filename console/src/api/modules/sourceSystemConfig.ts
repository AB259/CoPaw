import { request } from "../request";
import type { EffectiveSourceSystemConfig } from "../types/sourceSystemConfig";

export const sourceSystemConfigApi = {
  getEffective(): Promise<EffectiveSourceSystemConfig> {
    return request<EffectiveSourceSystemConfig>(
      "/source-system-config/effective",
    );
  },
};
