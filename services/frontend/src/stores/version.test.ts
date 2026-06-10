import { describe, it, expect, vi, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useVersionStore } from "./version";
import * as systemApi from "@/api/system";

vi.mock("@/api/system", () => ({
  getVersion: vi.fn(),
  triggerUpdate: vi.fn(),
}));

describe("useVersionStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("starts with idle state and no version", () => {
    const store = useVersionStore();
    expect(store.currentVersion).toBe("");
    expect(store.latestVersion).toBeNull();
    expect(store.loading).toBe(false);
    expect(store.hasUpdate).toBe(false);
  });

  it("checkVersion sets state on success with update", async () => {
    vi.mocked(systemApi.getVersion).mockResolvedValue({
      current_version: "0.4.5",
      latest_version: "0.5.0",
      update_available: true,
      last_checked: Date.now(),
      release_url: "https://github.com/test/test/releases/tag/v0.5.0",
    });

    const store = useVersionStore();
    await store.checkVersion();

    expect(store.currentVersion).toBe("0.4.5");
    expect(store.latestVersion).toBe("0.5.0");
    expect(store.hasUpdate).toBe(true);
    expect(store.loading).toBe(false);
  });

  it("checkVersion sets state when no update available", async () => {
    vi.mocked(systemApi.getVersion).mockResolvedValue({
      current_version: "0.5.0",
      latest_version: "0.5.0",
      update_available: false,
      last_checked: Date.now(),
      release_url: null,
    });

    const store = useVersionStore();
    await store.checkVersion();

    expect(store.currentVersion).toBe("0.5.0");
    expect(store.latestVersion).toBe("0.5.0");
    expect(store.hasUpdate).toBe(false);
  });

  it("checkVersion handles errors silently", async () => {
    vi.mocked(systemApi.getVersion).mockRejectedValue(new Error("Network error"));

    const store = useVersionStore();
    await store.checkVersion();

    // Errors are swallowed silently per design
    expect(store.loading).toBe(false);
    expect(store.hasUpdate).toBe(false);
  });

  it("dismiss stores version in localStorage", async () => {
    vi.mocked(systemApi.getVersion).mockResolvedValue({
      current_version: "0.4.5",
      latest_version: "0.5.0",
      update_available: true,
      last_checked: Date.now(),
      release_url: null,
    });

    const store = useVersionStore();
    await store.checkVersion();
    expect(store.hasUpdate).toBe(true);

    store.dismiss();
    expect(localStorage.getItem("dismissedVersion")).toBe("0.5.0");
    expect(store.hasUpdate).toBe(false);
  });

  it("respects dismissed version on next checkVersion call", async () => {
    // First check: version 0.5.0 available
    vi.mocked(systemApi.getVersion).mockResolvedValueOnce({
      current_version: "0.4.5",
      latest_version: "0.5.0",
      update_available: true,
      last_checked: Date.now(),
      release_url: null,
    });

    const store = useVersionStore();
    await store.checkVersion();
    expect(store.hasUpdate).toBe(true);
    store.dismiss();

    // Second check: same 0.5.0 still the latest — should stay dismissed
    vi.mocked(systemApi.getVersion).mockResolvedValueOnce({
      current_version: "0.4.5",
      latest_version: "0.5.0",
      update_available: true,
      last_checked: Date.now(),
      release_url: null,
    });
    await store.checkVersion();
    expect(store.hasUpdate).toBe(false);
  });

  it("re-shows banner when a newer version appears after dismiss", async () => {
    // First check: version 0.5.0 available, user dismisses
    vi.mocked(systemApi.getVersion).mockResolvedValueOnce({
      current_version: "0.4.5",
      latest_version: "0.5.0",
      update_available: true,
      last_checked: Date.now(),
      release_url: null,
    });

    const store = useVersionStore();
    await store.checkVersion();
    store.dismiss();

    // Second check: 0.6.0 now available — should re-appear
    vi.mocked(systemApi.getVersion).mockResolvedValueOnce({
      current_version: "0.4.5",
      latest_version: "0.6.0",
      update_available: true,
      last_checked: Date.now(),
      release_url: null,
    });
    await store.checkVersion();
    expect(store.hasUpdate).toBe(true);
  });
});
