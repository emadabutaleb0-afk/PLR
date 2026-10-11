"use client";
import dynamic from "next/dynamic";
import { Suspense } from "react";
import { useI18n } from "@/lib/i18n";
import { useApi } from "@/lib/hooks";
import { Page } from "@/components/Page";
import { LoadingBlock } from "@/components/States";

// React Flow is heavy: it is only downloaded when this page is opened.
const MapCanvas = dynamic(() => import("./MapCanvas"), { ssr: false, loading: () => <LoadingBlock h="h-[32rem]" /> });
export default function CommandMap() {
  const f = useApi<any>("/workspace/board");
  return <Page title="Command Map" sub="How products, locations, materials, suppliers and open decisions are really connected in your data." fresh={f.data?.freshness}><Suspense fallback={<LoadingBlock h="h-[32rem]" />}><MapCanvas /></Suspense></Page>;
}
