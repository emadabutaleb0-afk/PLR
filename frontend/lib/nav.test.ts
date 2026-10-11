import { describe, expect, it } from "vitest";
import { ALL_ITEMS, allowed, crumbs, contextActions } from "./nav";
import { ROLE_SCOPES } from "@/tests/roles";

const visible = (role: string) => ALL_ITEMS.filter((i) => allowed(i.scope, (s) => ROLE_SCOPES[role].has(s))).map((i) => i.href);

describe("role-aware navigation", () => {
  it("a store manager does not see finance, suppliers, user admin or analytics export", () => {
    const v = visible("STORE_MANAGER");
    for (const h of ["/users", "/suppliers", "/discounts", "/analytics", "/dashboard", "/autopsy"]) expect(v).not.toContain(h);
    expect(v).toContain("/notifications"); expect(v).toContain("/inventory");
  });
  it("only the CEO sees Users & Access", () => {
    expect(visible("CEO")).toContain("/users");
    expect(visible("EXECUTIVE")).not.toContain("/users");
  });
  it("every nav entry has a unique href", () => { const h = ALL_ITEMS.map((i) => i.href); expect(new Set(h).size).toBe(h.length); });
});
describe("breadcrumbs and context actions", () => {
  it("builds group > page > record", () => {
    expect(crumbs("/products/P-001").map((c) => c.label)).toEqual(["Control", "Products", "P-001"]);
    expect(crumbs("/war-room").map((c) => c.label)).toEqual(["Workspaces", "Decision War Room"]);
  });
  it("context actions are links only", () => { for (const a of contextActions("/products/P-001")) expect(a.href).toMatch(/^\//); });
});
