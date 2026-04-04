import { test, expect } from "@playwright/test";

const BACKEND = process.env.PLAYWRIGHT_BACKEND_URL ?? "http://localhost:8000";

test.describe("Onboarding page", () => {
  test("guide, checklist, and flow toggle work with a logged-in session", async ({ page, request }) => {
    const id = `e2e-onb-${Date.now()}`;
    const reg = await request.post(`${BACKEND}/api/auth/register`, {
      headers: { "Content-Type": "application/json" },
      data: JSON.stringify({
        login_id: id,
        name: "E2E Onboarding",
        password: "e2e-pass-9",
      }),
    });
    expect(reg.status()).toBe(201);
    const { access_token: token } = (await reg.json()) as { access_token: string };

    await page.context().addInitScript((t: string) => {
      localStorage.setItem("token", t);
    }, token);

    await page.goto("/onboarding/");
    await expect(page.getByRole("heading", { name: "Data pipeline onboarding" })).toBeVisible({
      timeout: 30_000,
    });

    await expect(page.getByText("Could not load status")).not.toBeVisible();
    await expect(page.getByText("AEP getting started")).toBeVisible();
    await expect(page.getByText(/1\.\s*AEP authentication/)).toBeVisible();
    await expect(page.getByText("NEXT").first()).toBeVisible();

    await page.getByRole("button", { name: "View as flow" }).click();
    await expect(page.getByRole("button", { name: "Back to guide" })).toBeVisible();
    await page.getByRole("button", { name: "Back to guide" }).click();
    await expect(page.getByRole("button", { name: "View as flow" })).toBeVisible();
  });
});
