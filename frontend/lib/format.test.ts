import { describe, expect, it } from "vitest";
import { egp, pct, num, ACTION_LABEL } from "./format";
import { i18nState, translate } from "./i18n";
import { AR } from "./ar";
describe("format", () => {
  it("formats EGP compactly and exactly", () => { i18nState.lang = "en"; expect(egp(1_250_000)).toBe("EGP 1.25M"); expect(egp(12_345, false)).toBe("EGP 12,345"); expect(egp(null)).toBe("—"); });
  it("formats EGP in Arabic", () => { i18nState.lang = "ar"; expect(egp(1_250_000)).toBe("1.25 مليون ج.م"); expect(egp(12_345, false)).toBe("12,345 ج.م"); i18nState.lang = "en"; });
  it("formats percentages and numbers", () => { expect(pct(0.1531)).toBe("15.3%"); expect(pct(undefined)).toBe("—"); expect(num(1234.5)).toBe("1,235"); });
  it("uses business language for actions", () => { expect(ACTION_LABEL.RELOCATE).toBe("Transfer"); expect(ACTION_LABEL.STOP_REPLENISHMENT).toBe("Stop replenishing"); });
});
describe("i18n", () => {
  it("translates, falls back to English and fills variables", () => {
    expect(translate("ar", "Sign in")).toBe("تسجيل الدخول");
    expect(translate("ar", "not in the dictionary")).toBe("not in the dictionary");
    expect(translate("en", "Sign in")).toBe("Sign in");
    expect(translate("ar", "{n} company files were found. Load them once to build the dashboards and recommendations.", { n: 20 })).toContain("20");
  });
  it("has an Arabic text for every action label", () => { for (const v of Object.values(ACTION_LABEL)) expect(AR[v], v).toBeTruthy(); });
});
