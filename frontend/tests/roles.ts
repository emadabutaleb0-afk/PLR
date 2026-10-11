// Test-only copy of backend/app/auth/rbac.py ROLE_SCOPES (copied from it; update both together). The real check is always server side.
export const ROLE_SCOPES: Record<string, Set<string>> = {
  CEO: new Set(["actions", "alerts", "audit_view", "costs", "data_health", "data_import", "decide", "executive", "export", "inventory", "marketing", "models", "operations", "products", "quality", "recovery", "suppliers", "users_admin", "value"]),
  EXECUTIVE: new Set(["actions", "alerts", "audit_view", "costs", "data_health", "decide", "executive", "export", "inventory", "marketing", "models", "operations", "products", "quality", "recovery", "suppliers", "value"]),
  OPERATIONS_MANAGER: new Set(["actions", "alerts", "costs", "data_health", "data_import", "decide", "executive", "export", "inventory", "operations", "products", "quality", "recovery", "suppliers", "value"]),
  PRODUCTION_MANAGER: new Set(["actions", "alerts", "data_health", "decide", "operations", "products", "quality", "recovery", "suppliers"]),
  MARKETING_MANAGER: new Set(["actions", "alerts", "decide", "export", "inventory", "marketing", "products", "value"]),
  STORE_MANAGER: new Set(["actions", "alerts", "decide", "inventory", "products"]),
  ANALYST: new Set(["actions", "alerts", "costs", "data_health", "data_import", "executive", "export", "inventory", "marketing", "models", "operations", "products", "quality", "recovery", "suppliers", "value"]),
};
