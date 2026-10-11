import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const apiMock = vi.fn();
let scopes = new Set(["decide", "recovery"]);
vi.mock("@/lib/api", () => ({ api: (...a: any[]) => apiMock(...a), download: vi.fn() }));
vi.mock("@/lib/auth", () => ({ useAuth: () => ({ can: (s: string) => scopes.has(s), user: { email: "x@y.z" } }) }));
vi.mock("next/link", () => ({ default: ({ href, children, ...p }: any) => <a href={href} {...p}>{children}</a> }));
const REC = { rec_key: "k1", title: "Move 40 units to Cairo", problem: "Stock out soon", action: "Transfer 40 units", status: "OPEN", urgency: "HIGH", department: "Inventory",
  estimated_value_egp: 12000, estimated_loss_egp: 0, confidence: 0.7, is_estimate: true, impact_type: "revenue_protected", why: ["Cover is 3 days"], product_id: "P1", evidence: {} };
vi.mock("@/lib/hooks", () => ({ useApi: (path: string | null) => ({ data: !path ? undefined : path.startsWith("/workspace") ? { events: [] } : REC, isLoading: false, isError: false }) }));

import { DecisionDrawer } from "./DecisionDrawer";
const wrap = () => render(<QueryClientProvider client={new QueryClient()}><DecisionDrawer recKey="k1" onClose={() => {}} onDone={() => {}} /></QueryClientProvider>);

describe("DecisionDrawer: approval is always an explicit, confirmed, server-checked step", () => {
  beforeEach(() => { apiMock.mockReset(); apiMock.mockResolvedValue({ status: "ACCEPTED" }); scopes = new Set(["decide", "recovery"]); });

  it("clicking Approve only opens a confirmation; nothing is sent yet", async () => {
    wrap(); await userEvent.click(screen.getByRole("button", { name: /approve/i }));
    expect(await screen.findByRole("alertdialog")).toBeTruthy();
    expect(apiMock).not.toHaveBeenCalled();
  });
  it("Cancel closes the confirmation without calling the API", async () => {
    wrap(); await userEvent.click(screen.getByRole("button", { name: /approve/i }));
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("alertdialog")).toBeNull(); expect(apiMock).not.toHaveBeenCalled();
  });
  it("confirming posts exactly one feedback request to the existing endpoint", async () => {
    wrap(); await userEvent.click(screen.getByRole("button", { name: /approve/i }));
    const dlg = await screen.findByRole("alertdialog");
    await userEvent.click(dlg.querySelectorAll("button")[1] as HTMLElement);
    await waitFor(() => expect(apiMock).toHaveBeenCalledTimes(1));
    const [path, opts] = apiMock.mock.calls[0]; expect(path).toBe("/recommendations/k1/feedback"); expect(JSON.parse(opts.body).decision).toBe("ACCEPT");
  });
  it("a server refusal is shown and never reported as success", async () => {
    apiMock.mockRejectedValue(Object.assign(new Error("Newest business data is 40 days old."), { status: 409 }));
    wrap(); await userEvent.click(screen.getByRole("button", { name: /approve/i }));
    const dlg = await screen.findByRole("alertdialog"); await userEvent.click(dlg.querySelectorAll("button")[1] as HTMLElement);
    expect(await screen.findByText(/40 days old/)).toBeTruthy(); expect(screen.getByRole("alertdialog")).toBeTruthy();
  });
  it("a role without the decide scope sees the decision but no approve buttons", () => {
    scopes = new Set(["recovery"]); wrap();
    expect(screen.queryByRole("button", { name: /approve/i })).toBeNull(); expect(screen.getByText(/can view this decision but not approve/i)).toBeTruthy();
  });
  it("labels the expected value as an estimate", () => { wrap(); expect(screen.getAllByText(/estimate/i).length).toBeGreaterThan(0); });
});
