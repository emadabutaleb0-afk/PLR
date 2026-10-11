# Data model
Generated from `backend/app/ingestion/specs.py` (single source of truth for columns, types, keys, FKs and validation rules). Column names are lower-cased CSV headers.

## Enforced foreign keys (real relationships only)
| Child | Column | Parent |
|---|---|---|
| sales_transactions | product_id / customer_id / location_id | product_master / customers / locations |
| inventory_history | product_id / location_id | product_master / locations |
| marketing, quality, production_orders, printing_batches, product_bom | product_id | product_master |
| product_bom | material_id | materials |
| purchase_orders | material_id / supplier_id | materials / suppliers |

## Documented aggregated (non-FK) relationships
| Link | How it is used | Limit |
|---|---|---|
| printing_batches.machine_id ↔ machine_downtime.machine_id | warning if unknown; joined for printing machines | machine_downtime has other machine families and no machine master |
| product → bom → material → purchase_orders → supplier | spend-weighted supplier score per product | aggregated, not PO-to-production-order |
| customer_service ↔ sales/quality | monthly series, Spearman association | no product/invoice key |
| marketing ↔ sales | product + date window | attributed revenue is modelled, not reconciled |

## Application tables
users, audit_logs, data_refresh_runs, file_health, data_quality_issues, quarantine_rows, recommendations, recommendation_feedback, action_items, alerts, jobs, model_registry, analytics_snapshots.

## Validation (per file)
required columns · types · nulls · duplicate keys · foreign keys · invalid/implausible dates · negative or impossible quantities · cross-column sums (good+rejected=produced, accepted+rejected=ordered, passed+rejected=inspected) · staleness · soft links. Invalid rows are quarantined with a plain-language reason; the literal text `None` is preserved as a real category.
