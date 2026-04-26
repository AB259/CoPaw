import React, { useEffect } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { Form } from "antd";
import type { FormInstance } from "antd";
import { describe, expect, it, vi } from "vitest";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

import { LlmRateLimiterCard } from "./LlmRateLimiterCard";

const initialValues = {
  llm_max_concurrent: 10,
  llm_chat_max_concurrent: 4,
  llm_cron_max_concurrent: 2,
  llm_max_qpm: 600,
  llm_rate_limit_pause: 5,
  llm_rate_limit_jitter: 1,
  llm_acquire_timeout: 300,
  llm_chat_acquire_timeout: 30,
  llm_cron_acquire_timeout: 90,
};

function RateLimiterHarness({
  onFormReady,
}: {
  onFormReady: (form: FormInstance) => void;
}) {
  const [form] = Form.useForm();

  useEffect(() => {
    onFormReady(form);
  }, [form, onFormReady]);

  return (
    <Form form={form} layout="vertical" initialValues={initialValues}>
      <LlmRateLimiterCard />
    </Form>
  );
}

describe("LlmRateLimiterCard", () => {
  it("submits workload-specific limiter overrides with the running config", async () => {
    let form: FormInstance | undefined;

    render(<RateLimiterHarness onFormReady={(value) => (form = value)} />);

    expect(
      screen.getByText("agentConfig.llmChatMaxConcurrent"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("agentConfig.llmCronMaxConcurrent"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("agentConfig.llmChatAcquireTimeout"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("agentConfig.llmCronAcquireTimeout"),
    ).toBeInTheDocument();

    await waitFor(() => expect(form).toBeDefined());

    await expect(form!.validateFields()).resolves.toMatchObject({
      llm_chat_max_concurrent: 4,
      llm_cron_max_concurrent: 2,
      llm_chat_acquire_timeout: 30,
      llm_cron_acquire_timeout: 90,
    });
  });
});
