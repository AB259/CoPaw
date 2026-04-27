import { describe, it, expect } from "vitest";
import {
  generateCronExpression,
  validateHour,
  validateMinute,
  formatTimeValue,
  parseTimeString,
  weekdayLabelToNumber,
  weekdayNumberToLabel,
  calculateNextRun,
  formatNextRunPreview,
  hasDateBoundaryWarning,
  WEEKDAY_MAP,
  type ScheduleConfig,
} from "./cron";
import dayjs from "dayjs";

describe("generateCronExpression", () => {
  it("generates daily cron expression", () => {
    const result = generateCronExpression({ frequency: "daily", hour: 9, minute: 0 });
    expect(result).toBe("00 09 * * *");
  });

  it("generates weekly cron expression", () => {
    const result = generateCronExpression({
      frequency: "weekly",
      hour: 10,
      minute: 30,
      weekdays: [1, 3, 5],
    });
    expect(result).toBe("30 10 * * 1,3,5");
  });

  it("converts Sunday (0) to cron standard (7)", () => {
    const result = generateCronExpression({
      frequency: "weekly",
      hour: 10,
      minute: 0,
      weekdays: [0, 1],
    });
    expect(result).toBe("00 10 * * 1,7");
  });

  it("generates monthly cron expression", () => {
    const result = generateCronExpression({
      frequency: "monthly",
      hour: 10,
      minute: 0,
      dates: [1, 15],
    });
    expect(result).toBe("00 10 1,15 * *");
  });

  it("throws for weekly without weekdays", () => {
    expect(() =>
      generateCronExpression({ frequency: "weekly", hour: 10, minute: 0 })
    ).toThrow("Weekly frequency requires at least one weekday");
  });

  it("throws for monthly without dates", () => {
    expect(() =>
      generateCronExpression({ frequency: "monthly", hour: 10, minute: 0 })
    ).toThrow("Monthly frequency requires at least one date");
  });
});

describe("validateHour", () => {
  it("returns valid hour unchanged", () => {
    expect(validateHour(9)).toBe(9);
    expect(validateHour("09")).toBe(9);
  });

  it("clamps hour above 23 to 23", () => {
    expect(validateHour(25)).toBe(23);
    expect(validateHour("25")).toBe(23);
  });

  it("clamps negative hour to 0", () => {
    expect(validateHour(-1)).toBe(0);
  });

  it("returns 0 for invalid input", () => {
    expect(validateHour("abc")).toBe(0);
    expect(validateHour(NaN)).toBe(0);
  });
});

describe("validateMinute", () => {
  it("returns valid minute unchanged", () => {
    expect(validateMinute(30)).toBe(30);
    expect(validateMinute("30")).toBe(30);
  });

  it("clamps minute above 59 to 59", () => {
    expect(validateMinute(99)).toBe(59);
    expect(validateMinute("99")).toBe(59);
  });

  it("clamps negative minute to 0", () => {
    expect(validateMinute(-1)).toBe(0);
  });

  it("returns 0 for invalid input", () => {
    expect(validateMinute("abc")).toBe(0);
    expect(validateMinute(NaN)).toBe(0);
  });
});

describe("formatTimeValue", () => {
  it("pads single digit with zero", () => {
    expect(formatTimeValue(9)).toBe("09");
    expect(formatTimeValue(0)).toBe("00");
  });

  it("returns double digit unchanged", () => {
    expect(formatTimeValue(10)).toBe("10");
    expect(formatTimeValue(23)).toBe("23");
  });
});

describe("parseTimeString", () => {
  it("parses valid time string", () => {
    expect(parseTimeString("09:30")).toEqual({ hour: 9, minute: 30 });
  });

  it("returns default for invalid format", () => {
    expect(parseTimeString("invalid")).toEqual({ hour: 9, minute: 0 });
    expect(parseTimeString("9")).toEqual({ hour: 9, minute: 0 });
  });

  it("validates parsed values", () => {
    expect(parseTimeString("25:99")).toEqual({ hour: 23, minute: 59 });
  });
});

describe("weekdayLabelToNumber", () => {
  it("maps Chinese labels correctly", () => {
    expect(weekdayLabelToNumber("一")).toBe(1);
    expect(weekdayLabelToNumber("二")).toBe(2);
    expect(weekdayLabelToNumber("日")).toBe(0);
  });

  it("returns 0 for unknown label", () => {
    expect(weekdayLabelToNumber("X")).toBe(0);
  });
});

describe("weekdayNumberToLabel", () => {
  it("converts numbers to Chinese labels", () => {
    expect(weekdayNumberToLabel(1)).toBe("一");
    expect(weekdayNumberToLabel(5)).toBe("五");
    expect(weekdayNumberToLabel(0)).toBe("日");
    expect(weekdayNumberToLabel(7)).toBe("日");
  });

  it("returns empty string for invalid number", () => {
    expect(weekdayNumberToLabel(8)).toBe("");
  });
});

describe("calculateNextRun", () => {
  it("calculates next daily run (same day if time not passed)", () => {
    const now = dayjs();
    const futureHour = now.hour() + 1;
    const config: ScheduleConfig = { frequency: "daily", hour: futureHour, minute: 0 };
    const nextRun = calculateNextRun(config);
    expect(nextRun.hour()).toBe(futureHour);
    expect(nextRun.isAfter(now)).toBe(true);
  });

  it("calculates next daily run (next day if time passed)", () => {
    const now = dayjs();
    const pastHour = now.hour() - 1;
    const config: ScheduleConfig = { frequency: "daily", hour: pastHour, minute: 0 };
    const nextRun = calculateNextRun(config);
    expect(nextRun.date()).toBe(now.add(1, "day").date());
  });

  it("calculates next weekly run", () => {
    const config: ScheduleConfig = { frequency: "weekly", hour: 10, minute: 0, weekdays: [1, 3, 5] };
    const nextRun = calculateNextRun(config);
    const dayOfWeek = nextRun.day() === 0 ? 7 : nextRun.day();
    expect([1, 3, 5]).toContain(dayOfWeek);
  });

  it("calculates next monthly run", () => {
    const config: ScheduleConfig = { frequency: "monthly", hour: 10, minute: 0, dates: [1, 15] };
    const nextRun = calculateNextRun(config);
    expect([1, 15]).toContain(nextRun.date());
  });
});

describe("formatNextRunPreview", () => {
  it("formats daily preview", () => {
    const config: ScheduleConfig = { frequency: "daily", hour: 9, minute: 0 };
    const preview = formatNextRunPreview(config);
    expect(preview).toContain("09:00");
    expect(preview).toContain("每天自动执行");
  });

  it("formats weekly preview with weekdays", () => {
    const config: ScheduleConfig = { frequency: "weekly", hour: 10, minute: 0, weekdays: [1, 3, 5] };
    const preview = formatNextRunPreview(config);
    expect(preview).toContain("10:00");
    expect(preview).toContain("每周一三五执行");
  });

  it("formats monthly preview with dates", () => {
    const config: ScheduleConfig = { frequency: "monthly", hour: 10, minute: 0, dates: [1, 15] };
    const preview = formatNextRunPreview(config);
    expect(preview).toContain("10:00");
    expect(preview).toContain("每月1日、15日执行");
  });
});

describe("hasDateBoundaryWarning", () => {
  it("returns false for dates below 29", () => {
    expect(hasDateBoundaryWarning([1, 15])).toBe(false);
    expect(hasDateBoundaryWarning([28])).toBe(false);
  });

  it("returns true for dates 29, 30, 31", () => {
    expect(hasDateBoundaryWarning([29])).toBe(true);
    expect(hasDateBoundaryWarning([30])).toBe(true);
    expect(hasDateBoundaryWarning([31])).toBe(true);
    expect(hasDateBoundaryWarning([1, 31])).toBe(true);
  });
});