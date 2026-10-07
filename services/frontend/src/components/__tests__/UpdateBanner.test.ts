import { describe, it, expect, vi, beforeEach } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import UpdateBanner from "@/components/UpdateBanner.vue";
import { useAuthStore } from "@/stores/auth";
import * as systemApi from "@/api/system";

vi.mock("@/api/system", () => ({
  getVersion: vi.fn(),
}));

function versionResponse(update_available: boolean) {
  return {
    current_version: "1.0.0-rc.1",
    latest_version: "1.0.0",
    update_available,
    last_checked: Date.now(),
    release_url: "https://github.com/test/test/releases/tag/v1.0.0",
  };
}

async function mountBanner(update_available: boolean) {
  vi.mocked(systemApi.getVersion).mockResolvedValue(versionResponse(update_available));
  useAuthStore().setToken({ accessToken: "t", expiresAt: Date.now() / 1000 + 3600 } as never);
  const wrapper = mount(UpdateBanner);
  await flushPromises();
  return wrapper;
}

describe("UpdateBanner", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("renders nothing when no update available", async () => {
    const wrapper = await mountBanner(false);
    expect(wrapper.find('[data-testid="update-banner"]').exists()).toBe(false);
  });

  it("shows release notes link but no button that executes an update", async () => {
    const wrapper = await mountBanner(true);
    expect(wrapper.find('[data-testid="update-banner"]').exists()).toBe(true);
    expect(wrapper.find('a[href$="/v1.0.0"]').exists()).toBe(true);
    expect(wrapper.text()).not.toContain("Aktualisieren");
  });

  it("shows runbook commands pinned to docker-compose.yml incl. migration", async () => {
    const wrapper = await mountBanner(true);
    await wrapper.find('[data-testid="show-instructions"]').trigger("click");
    const text = wrapper.find("pre").text();
    expect(text).toContain("docker compose -f docker-compose.yml build");
    expect(text).toContain("docker compose -f docker-compose.yml run --no-deps --rm --build migrate alembic upgrade head");
    expect(text).toContain("docker compose -f docker-compose.yml up -d");
    expect(text).not.toMatch(/docker compose (pull|up)/);
  });

  it("can be dismissed", async () => {
    const wrapper = await mountBanner(true);
    await wrapper.find('[data-testid="dismiss-update"]').trigger("click");
    expect(localStorage.getItem("dismissedVersion")).toBe("1.0.0");
    expect(wrapper.find('[data-testid="update-banner"]').exists()).toBe(false);
  });
});
