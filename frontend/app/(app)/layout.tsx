import AppShell from "@/components/AppShell";
import { DataGate } from "@/components/DataGate";
export default function L({ children }: { children: React.ReactNode }) { return <AppShell><DataGate>{children}</DataGate></AppShell>; }
