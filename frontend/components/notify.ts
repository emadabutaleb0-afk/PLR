import { AlertTriangle, BellRing, Clock, Database, FileCheck2, TrendingUp } from "lucide-react";
export const KIND_LABEL: Record<string, string> = { approval: "Pending approval", alert: "Alert", data_quality: "Data quality", delayed_action: "Delayed action", outcome: "Workflow update" };
export const KIND_ICON: Record<string, any> = { approval: FileCheck2, alert: AlertTriangle, data_quality: Database, delayed_action: Clock, outcome: TrendingUp, default: BellRing };
