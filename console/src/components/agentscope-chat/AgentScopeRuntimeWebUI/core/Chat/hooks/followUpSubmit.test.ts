import { describe, expect, it, vi } from "vitest";
import {
  FollowUpSubmitCoordinator,
  FOLLOW_UP_STOP_BACKOFF_MS,
} from "./followUpSubmit";

describe("FollowUpSubmitCoordinator", () => {
  it("stops the active run first and only auto-submits after generation ends", async () => {
    let generating = true;
    const stop = vi.fn(async () => {
      generating = false;
    });
    const submit = vi.fn(async () => {});
    const restoreInput = vi.fn();
    const notifyFailure = vi.fn();
    const sleepMs = vi.fn(async () => {});

    const coordinator = new FollowUpSubmitCoordinator(
      {
        stop,
        submit,
        isGenerating: async () => generating,
        restoreInput,
        notifyFailure,
        sleepMs,
      },
      FOLLOW_UP_STOP_BACKOFF_MS,
    );

    const task = coordinator.enqueue({
      query: "latest question",
      fileList: [],
    });

    expect(submit).not.toHaveBeenCalled();

    await task;

    expect(stop).toHaveBeenCalledTimes(1);
    expect(submit).toHaveBeenCalledWith({
      query: "latest question",
      fileList: [],
    });
    expect(restoreInput).not.toHaveBeenCalled();
    expect(notifyFailure).not.toHaveBeenCalled();
  });

  it("keeps only the latest pending follow-up message while stop is in progress", async () => {
    let generating = true;
    let releaseStop: (() => void) | null = null;
    const stop = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          releaseStop = () => {
            generating = false;
            resolve();
          };
        }),
    );
    const submit = vi.fn(async () => {});

    const coordinator = new FollowUpSubmitCoordinator({
      stop,
      submit,
      isGenerating: async () => generating,
      restoreInput: vi.fn(),
      notifyFailure: vi.fn(),
      sleepMs: vi.fn(async () => {}),
    });

    const first = coordinator.enqueue({ query: "first" });
    coordinator.enqueue({ query: "second" });

    expect(submit).not.toHaveBeenCalled();

    releaseStop?.();
    await first;

    expect(stop).toHaveBeenCalledTimes(1);
    expect(submit).toHaveBeenCalledTimes(1);
    expect(submit).toHaveBeenCalledWith({ query: "second" });
  });

  it("restores the latest pending input and reports failure when stop retry budget is exhausted", async () => {
    const stop = vi.fn(async () => {});
    const submit = vi.fn(async () => {});
    const restoreInput = vi.fn();
    const notifyFailure = vi.fn();
    const sleepMs = vi.fn(async () => {});

    const coordinator = new FollowUpSubmitCoordinator(
      {
        stop,
        submit,
        isGenerating: async () => true,
        restoreInput,
        notifyFailure,
        sleepMs,
      },
      [10, 20],
    );

    await coordinator.enqueue({ query: "recover me" });

    expect(stop).toHaveBeenCalledTimes(3);
    expect(sleepMs).toHaveBeenCalledTimes(2);
    expect(submit).not.toHaveBeenCalled();
    expect(restoreInput).toHaveBeenCalledWith("recover me");
    expect(notifyFailure).toHaveBeenCalledTimes(1);
  });
});
