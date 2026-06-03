import type { AgenticRunResponse, CFRecommendationResponse, ComparisonResponse } from "@/lib/api";

const SELECTED_USER_ID_KEY = "lili:selected-user-id";
const AGENTIC_RESULT_KEY = "lili:agentic-result";
const CF_RESULT_KEY = "lili:cf-result";
const COMPARISON_RESULT_KEY = "lili:comparison-result";

type PersistedAgenticResult = {
  result: AgenticRunResponse;
};

type PersistedCFResult = {
  result: CFRecommendationResponse;
};

type PersistedComparisonResult = {
  result: ComparisonResponse;
};

function canUseStorage() {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

export function readSelectedUserId() {
  if (!canUseStorage()) {
    return null;
  }

  return window.localStorage.getItem(SELECTED_USER_ID_KEY);
}

export function writeSelectedUserId(userId: string) {
  if (!canUseStorage()) {
    return;
  }

  window.localStorage.setItem(SELECTED_USER_ID_KEY, userId);
}

export function readPersistedAgenticResult(): AgenticRunResponse | null {
  if (!canUseStorage()) {
    return null;
  }

  const rawValue = window.localStorage.getItem(AGENTIC_RESULT_KEY);
  if (!rawValue) {
    return null;
  }

  try {
    const parsed = JSON.parse(rawValue) as PersistedAgenticResult;
    return parsed?.result ?? null;
  } catch {
    return null;
  }
}

export function writePersistedAgenticResult(result: AgenticRunResponse) {
  if (!canUseStorage()) {
    return;
  }

  const payload: PersistedAgenticResult = { result };
  window.localStorage.setItem(AGENTIC_RESULT_KEY, JSON.stringify(payload));
}

export function readPersistedCFResult(): CFRecommendationResponse | null {
  if (!canUseStorage()) {
    return null;
  }

  const rawValue = window.localStorage.getItem(CF_RESULT_KEY);
  if (!rawValue) {
    return null;
  }

  try {
    const parsed = JSON.parse(rawValue) as PersistedCFResult;
    return parsed?.result ?? null;
  } catch {
    return null;
  }
}

export function writePersistedCFResult(result: CFRecommendationResponse) {
  if (!canUseStorage()) {
    return;
  }

  const payload: PersistedCFResult = { result };
  window.localStorage.setItem(CF_RESULT_KEY, JSON.stringify(payload));
}

export function readPersistedComparisonResult(): ComparisonResponse | null {
  if (!canUseStorage()) {
    return null;
  }

  const rawValue = window.localStorage.getItem(COMPARISON_RESULT_KEY);
  if (!rawValue) {
    return null;
  }

  try {
    const parsed = JSON.parse(rawValue) as PersistedComparisonResult;
    return parsed?.result ?? null;
  } catch {
    return null;
  }
}

export function writePersistedComparisonResult(result: ComparisonResponse) {
  if (!canUseStorage()) {
    return;
  }

  const payload: PersistedComparisonResult = { result };
  window.localStorage.setItem(COMPARISON_RESULT_KEY, JSON.stringify(payload));
}
