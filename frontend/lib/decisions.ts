"use client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";

export const recPath = (key: string) => encodeURIComponent(key).replace(/%3A/g, ":");
export type Verb = "ACCEPT" | "DEFER" | "REJECT";
/** Every approval goes through the existing backend endpoint, which checks the role, the stale-data guard and writes the audit log. The UI never assumes success. */
export function useDecide() {
  const qc = useQueryClient();
  const feedback = useMutation({
    mutationFn: (v: { key: string; decision: Verb; comment?: string; acknowledgeStale?: boolean }) =>
      api(`/recommendations/${recPath(v.key)}/feedback`, { method: "POST", body: JSON.stringify({ decision: v.decision, comment: v.comment || null, acknowledge_stale: !!v.acknowledgeStale }) }),
    onSuccess: () => qc.invalidateQueries(),
  });
  const patchAction = useMutation({
    mutationFn: (v: { id: number; status?: string; owner_email?: string }) => api(`/actions/${v.id}`, { method: "PATCH", body: JSON.stringify({ status: v.status, owner_email: v.owner_email }) }),
    onSuccess: () => qc.invalidateQueries(),
  });
  return { feedback, patchAction };
}
/** What dropping a card on a lane would do, or null when the move is not a valid workflow step. Validity here only prevents silly drops: the server is the authority. */
export function moveFor(card: { lane: string; action_id?: number }, to: string): { kind: "feedback"; decision: Verb } | { kind: "action"; status: string } | null {
  if ((card.lane === "open" || card.lane === "deferred") && to === "approved") return { kind: "feedback", decision: "ACCEPT" };
  if (card.lane === "open" && to === "deferred") return { kind: "feedback", decision: "DEFER" };
  if ((card.lane === "open" || card.lane === "deferred") && to === "rejected") return { kind: "feedback", decision: "REJECT" };
  if (card.lane === "approved" && to === "in_progress" && card.action_id) return { kind: "action", status: "IN_PROGRESS" };
  if (card.lane === "in_progress" && to === "measuring" && card.action_id) return { kind: "action", status: "DONE" };
  return null;
}
