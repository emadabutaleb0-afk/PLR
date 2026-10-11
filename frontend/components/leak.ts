export const LEAK_COLOR: Record<string, string> = { production: "#1f2937", quality: "#64748b", returns: "#a8a29e", stockouts: "#e11d48", discounts: "#b58a3a" };
export const LEAK_KEYS = ["production", "quality", "returns", "stockouts", "discounts"] as const;
export const LEAK_LABEL: Record<string, string> = { production: "Production & print waste", quality: "Quality loss", returns: "Returns & refunds", stockouts: "Stockout opportunity loss", discounts: "Discount leakage" };
