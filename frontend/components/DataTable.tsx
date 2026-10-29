"use client";
import { ColumnDef, flexRender, getCoreRowModel, useReactTable, VisibilityState } from "@tanstack/react-table";
import { useEffect, useRef, useState } from "react";
import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight, Columns3, Download, Search, X } from "lucide-react";
import { Button, Card, Input, Select, Skeleton } from "./ui/primitives";
import { Empty } from "./States";
import { download } from "@/lib/api";
import { num } from "@/lib/format";
import { useI18n } from "@/lib/i18n";

export type Query = { page: number; page_size: number; sort?: string; order: "asc" | "desc"; q: string };

/** Enterprise table: server-side pagination/sort/search, column visibility, sticky header, export. Only one page is ever fetched. Column `header` strings are English keys and are translated here. */
export function DataTable<T extends object>({
  columns,
  data,
  total,
  pages,
  query,
  setQuery,
  loading,
  exportPath,
  exportName,
  filters,
  empty,
}: {
  columns: ColumnDef<T, any>[];
  data: T[];
  total: number;
  pages: number;
  query: Query;
  setQuery: (q: Query) => void;
  loading?: boolean;
  exportPath?: string;
  exportName?: string;
  filters?: React.ReactNode;
  empty?: string;
}) {
  const { t, isAr } = useI18n();
  const [vis, setVis] = useState<VisibilityState>({});
  const [colMenu, setColMenu] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [text, setText] = useState(query.q);
  const menuRef = useRef<HTMLDivElement>(null);

  // debounce the search box so we do not hit the server on every keystroke
  useEffect(() => {
    if (text === query.q) return;
    const id = setTimeout(() => setQuery({ ...query, q: text, page: 1 }), 300);
    return () => clearTimeout(id);
  }, [text]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!colMenu) return;
    const f = (e: MouseEvent) => {
      if (!menuRef.current?.contains(e.target as Node)) setColMenu(false);
    };
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") setColMenu(false);
    };
    document.addEventListener("mousedown", f);
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("mousedown", f);
      document.removeEventListener("keydown", key);
    };
  }, [colMenu]);

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    state: { columnVisibility: vis },
    onColumnVisibilityChange: setVis,
    manualPagination: true,
    manualSorting: true,
  });

  const doExport = async () => {
    if (!exportPath) return;
    setExporting(true);
    try {
      await download(exportPath, exportName || "export.csv");
    } catch (e: any) {
      alert(e.message);
    } finally {
      setExporting(false);
    }
  };

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-wrap items-center gap-2 border-b border-line p-3">
        <div className="relative w-full max-w-xs">
          <Search className="absolute start-3 top-2.5 h-4 w-4 text-slate-400" />
          <Input
            className="ps-9 pe-8"
            placeholder={t("Search…")}
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          {text && (
            <button
              type="button"
              onClick={() => {
                setText("");
                setQuery({ ...query, q: "", page: 1 });
              }}
              aria-label={t("clear")}
              className="absolute end-2.5 top-2.5 text-slate-400 hover:text-slate-600"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
        {filters}
        <div className="ms-auto flex items-center gap-2">
          <div className="relative" ref={menuRef}>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setColMenu(!colMenu)}
              aria-expanded={colMenu}
              aria-haspopup="true"
            >
              <Columns3 className="h-4 w-4" />
              {t("Columns")}
            </Button>
            {colMenu && (
              <div className="absolute end-0 z-20 mt-1 max-h-72 w-52 overflow-auto rounded-xl border border-line bg-raised p-2 shadow-pop">
                {table.getAllLeafColumns().map((c) => (
                  <label
                    key={c.id}
                    className="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1 text-sm hover:bg-sunken"
                  >
                    <input
                      type="checkbox"
                      checked={c.getIsVisible()}
                      onChange={c.getToggleVisibilityHandler()}
                      className="accent-brand-600"
                    />
                    {t(String(c.columnDef.header))}
                  </label>
                ))}
              </div>
            )}
          </div>
          {exportPath && (
            <Button
              variant="outline"
              size="sm"
              disabled={exporting}
              loading={exporting}
              onClick={doExport}
            >
              <Download className="h-4 w-4" />
              {t("Export")}
            </Button>
          )}
        </div>
      </div>
      <div className="max-h-[560px] overflow-auto">
        <table className="sticky-th w-full text-sm">
          <thead className="bg-sunken text-start text-xs uppercase tracking-wide text-slate-500">
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((h) => {
                  const id = (h.column.columnDef as any).accessorKey as string | undefined;
                  const active = id && query.sort === id;
                  const label =
                    typeof h.column.columnDef.header === "string"
                      ? t(h.column.columnDef.header)
                      : flexRender(h.column.columnDef.header, h.getContext());
                  return (
                    <th
                      key={h.id}
                      className="whitespace-nowrap bg-sunken px-3 py-2.5 text-start font-medium"
                    >
                      {id ? (
                        <button
                          className="inline-flex items-center gap-1 hover:text-slate-900"
                          onClick={() =>
                            setQuery({
                              ...query,
                              sort: id,
                              order: active && query.order === "desc" ? "asc" : "desc",
                              page: 1,
                            })
                          }
                        >
                          {label}
                          {active &&
                            (query.order === "desc" ? (
                              <ArrowDown className="h-3 w-3" />
                            ) : (
                              <ArrowUp className="h-3 w-3" />
                            ))}
                        </button>
                      ) : (
                        label
                      )}
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>
          <tbody className="divide-y divide-line">
            {loading ? (
              Array.from({ length: 8 }).map((_, i) => (
                <tr key={i}>
                  <td colSpan={columns.length} className="p-2">
                    <Skeleton className="h-8" />
                  </td>
                </tr>
              ))
            ) : table.getRowModel().rows.length > 0 ? (
              table.getRowModel().rows.map((r) => (
                <tr key={r.id} className="transition-colors hover:bg-sunken/60">
                  {r.getVisibleCells().map((c) => (
                    <td key={c.id} className="px-3 py-2.5 align-top">
                      {flexRender(c.column.columnDef.cell, c.getContext())}
                    </td>
                  ))}
                </tr>
              ))
            ) : null}
          </tbody>
        </table>
        {!loading && data.length === 0 && (
          <div className="p-6">
            <Empty title={empty || "No rows match"} hint="Try clearing the search or filters." />
          </div>
        )}
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line p-3 text-sm text-slate-500">
        <span>
          {num(total)} {t("rows")}
        </span>
        <div className="flex items-center gap-2">
          <Select
            value={query.page_size}
            onChange={(e) => setQuery({ ...query, page_size: +e.target.value, page: 1 })}
          >
            {[10, 25, 50, 100].map((n) => (
              <option key={n} value={n}>
                {n} / {t("page")}
              </option>
            ))}
          </Select>
          <Button
            variant="outline"
            size="icon"
            aria-label={t("Previous page")}
            disabled={query.page <= 1}
            onClick={() => setQuery({ ...query, page: query.page - 1 })}
          >
            {isAr ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </Button>
          <span>
            {t("Page")} {num(query.page)} {t("of")} {num(Math.max(pages, 1))}
          </span>
          <Button
            variant="outline"
            size="icon"
            aria-label={t("Next page")}
            disabled={query.page >= pages}
            onClick={() => setQuery({ ...query, page: query.page + 1 })}
          >
            {isAr ? <ChevronLeft className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          </Button>
        </div>
      </div>
    </Card>
  );
}

export const defaultQuery = (sort?: string, page_size = 25): Query => ({
  page: 1,
  page_size,
  sort,
  order: "desc",
  q: "",
});

export const qs = (q: Query, extra: Record<string, string | undefined> = {}) => {
  const p = new URLSearchParams({
    page: String(q.page),
    page_size: String(q.page_size),
    order: q.order,
  });
  if (q.sort) p.set("sort", q.sort);
  if (q.q) p.set("q", q.q);
  Object.entries(extra).forEach(([k, v]) => v && p.set(k, v));
  return p.toString();
};
