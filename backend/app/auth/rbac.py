"""Role -> scope matrix. Scopes gate endpoints; 'costs' gates cost/margin fields; STORE_MANAGER is also row-restricted by location."""
ALL = {"executive", "products", "inventory", "marketing", "suppliers", "quality", "operations", "recovery", "actions", "alerts", "value", "data_health",
       "data_import", "export", "costs", "decide", "audit_view", "users_admin", "models"}

ROLE_SCOPES: dict[str, set[str]] = {
    "CEO": set(ALL),
    "EXECUTIVE": ALL - {"users_admin", "data_import"},
    "OPERATIONS_MANAGER": {"executive", "products", "inventory", "suppliers", "quality", "operations", "recovery", "actions", "alerts", "value", "data_health", "data_import", "export", "costs", "decide"},
    "PRODUCTION_MANAGER": {"products", "quality", "operations", "suppliers", "recovery", "actions", "alerts", "data_health", "decide"},
    "MARKETING_MANAGER": {"products", "inventory", "marketing", "actions", "alerts", "value", "decide", "export"},  # no suppliers / procurement, no cost fields
    "STORE_MANAGER": {"products", "inventory", "actions", "alerts", "decide"},                                     # location-restricted
    "ANALYST": {"executive", "products", "inventory", "marketing", "suppliers", "quality", "operations", "recovery", "actions", "alerts", "value", "data_health", "data_import", "export", "costs", "models"},
}
ROLES = list(ROLE_SCOPES)
COST_FIELDS = {"cogs_unit", "gp_unit", "gp_12m", "margin_12m", "stock_value", "cogs", "gross_profit", "margin", "stock_value_at_risk", "expected_loss", "gp", "gp_90d", "gmroi",
               "profit_per_inventory_day", "avg_inventory_cost", "margin_score", "margin_health_score", "contribution", "contribution_per_unit"}
PROCUREMENT_FIELDS = {"supplier_lead_time_days"}
