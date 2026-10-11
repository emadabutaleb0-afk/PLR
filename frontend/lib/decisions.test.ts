import { describe, expect, it } from "vitest";
import { moveFor } from "./decisions";

// Dragging a card is only a *request*. These tests pin down which requests the board even offers; the server still authorises each one.
describe("moveFor (board drag rules)", () => {
  it("offers approve / defer / reject only from open decisions", () => {
    expect(moveFor({ lane: "open" }, "approved")).toEqual({ kind: "feedback", decision: "ACCEPT" });
    expect(moveFor({ lane: "open" }, "deferred")).toEqual({ kind: "feedback", decision: "DEFER" });
    expect(moveFor({ lane: "open" }, "rejected")).toEqual({ kind: "feedback", decision: "REJECT" });
  });
  it("a deferred decision can still be approved or rejected but not deferred again", () => {
    expect(moveFor({ lane: "deferred" }, "approved")).toEqual({ kind: "feedback", decision: "ACCEPT" });
    expect(moveFor({ lane: "deferred" }, "deferred")).toBeNull();
  });
  it("closed and measured decisions cannot be dragged anywhere", () => {
    for (const lane of ["rejected", "measuring", "measured"]) for (const to of ["open", "approved", "deferred", "rejected", "in_progress"]) expect(moveFor({ lane }, to)).toBeNull();
  });
  it("execution steps need a real action item and never produce an approval", () => {
    expect(moveFor({ lane: "approved" }, "in_progress")).toBeNull();
    expect(moveFor({ lane: "approved", action_id: 7 }, "in_progress")).toEqual({ kind: "action", status: "IN_PROGRESS" });
    expect(moveFor({ lane: "in_progress", action_id: 7 }, "measuring")).toEqual({ kind: "action", status: "DONE" });
    expect(moveFor({ lane: "approved", action_id: 7 }, "approved")).toBeNull();
  });
});
