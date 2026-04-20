import { buildAuthHeaders } from "@/api/authHeaders";

export interface SuggestionsRequest {
  chatId: string;
  turnId: string;
  userMessage: string;
  assistantMessage: string;
}

interface SuggestionsResponse {
  returnCode?: string;
  errorMsg?: string;
  body?: {
    output?: {
      result?: {
        suggestions?: unknown;
        questions?: unknown;
      };
    };
  };
}

const MOCK_DELAY = 500;
const DEFAULT_ENABLE_MOCK = true;

const MOCK_SUGGESTIONS = [
  "能给我一个总结吗",
  "下一步该怎么做",
  "有哪些风险点需要注意",
];

function normalizeSuggestions(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .filter((item): item is string => typeof item === "string")
    .map((item) => item.trim())
    .filter(Boolean);
}

function buildMockSuggestions(request: SuggestionsRequest): string[] {
  const trimmedUserMessage = request.userMessage.trim();
  if (!trimmedUserMessage) {
    return MOCK_SUGGESTIONS;
  }

  return [
    `关于“${trimmedUserMessage.slice(0, 12)}”能展开吗`,
    "能给我一个执行建议吗",
    "还有哪些补充信息",
  ];
}

export async function fetchSuggestions(
  request: SuggestionsRequest,
): Promise<string[]> {
  try {
    const baseUrl = window.__env__.baseUrl || "";
    const isDev = baseUrl === "yourapi";
    const useMock = DEFAULT_ENABLE_MOCK || isDev;
    if (useMock) {
      await new Promise((resolve) => setTimeout(resolve, MOCK_DELAY));
      return buildMockSuggestions(request);
    }

    const env = "prd";
    const apiKey = "your-api-key";
    const apiUrl = `${baseUrl}/openapi/${env}/your-suggestions-api`;

    const response = await fetch(apiUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "api-key": apiKey,
        ...buildAuthHeaders(),
      },
      body: JSON.stringify({
        inputParams: request,
      }),
    });

    if (!response.ok) {
      console.error("[Suggestions] API request failed:", response.status);
      return [];
    }

    const result: SuggestionsResponse = await response.json();
    return normalizeSuggestions(
      result.body?.output?.result?.suggestions ??
        result.body?.output?.result?.questions,
    );
  } catch (error) {
    console.error("[Suggestions] API request error:", error);
    return [];
  }
}
