# Browser walkthrough (V4)

Every screen of the web app was opened in a real Chromium browser, signed in as the CEO account, in English and in Arabic (RTL), against the 20 supplied company files, with the API running through **Redis + a Celery worker** (the import that filled the database was executed by the worker).

**Result: 54/54 page loads clean** (HTTP 200, no console errors, no failed `/api` calls, no error state shown).

| Page | EN | AR | Text chars (EN) | AR direction | Screenshots |
|---|---|---|---|---|---|
| `/` | ✅ | ✅ | 5,767 | rtl | [EN](screenshots/walkthrough/en_home.jpg) · [AR](screenshots/walkthrough/ar_home.jpg) |
| `/dashboard` | ✅ | ✅ | 2,716 | rtl | [EN](screenshots/walkthrough/en_dashboard.jpg) · [AR](screenshots/walkthrough/ar_dashboard.jpg) |
| `/demo` | ✅ | ✅ | 827 | rtl | [EN](screenshots/walkthrough/en_demo.jpg) · [AR](screenshots/walkthrough/ar_demo.jpg) |
| `/recovery` | ✅ | ✅ | 6,397 | rtl | [EN](screenshots/walkthrough/en_recovery.jpg) · [AR](screenshots/walkthrough/ar_recovery.jpg) |
| `/decisions` | ✅ | ✅ | 6,604 | rtl | [EN](screenshots/walkthrough/en_decisions.jpg) · [AR](screenshots/walkthrough/ar_decisions.jpg) |
| `/actions` | ✅ | ✅ | 982 | rtl | [EN](screenshots/walkthrough/en_actions.jpg) · [AR](screenshots/walkthrough/ar_actions.jpg) |
| `/alerts` | ✅ | ✅ | 9,482 | rtl | [EN](screenshots/walkthrough/en_alerts.jpg) · [AR](screenshots/walkthrough/ar_alerts.jpg) |
| `/autopsy` | ✅ | ✅ | 5,199 | rtl | [EN](screenshots/walkthrough/en_autopsy.jpg) · [AR](screenshots/walkthrough/ar_autopsy.jpg) |
| `/leakage` | ✅ | ✅ | 3,614 | rtl | [EN](screenshots/walkthrough/en_leakage.jpg) · [AR](screenshots/walkthrough/ar_leakage.jpg) |
| `/allocation` | ✅ | ✅ | 6,266 | rtl | [EN](screenshots/walkthrough/en_allocation.jpg) · [AR](screenshots/walkthrough/ar_allocation.jpg) |
| `/discounts` | ✅ | ✅ | 4,320 | rtl | [EN](screenshots/walkthrough/en_discounts.jpg) · [AR](screenshots/walkthrough/ar_discounts.jpg) |
| `/scenarios` | ✅ | ✅ | 3,569 | rtl | [EN](screenshots/walkthrough/en_scenarios.jpg) · [AR](screenshots/walkthrough/ar_scenarios.jpg) |
| `/supply` | ✅ | ✅ | 6,096 | rtl | [EN](screenshots/walkthrough/en_supply.jpg) · [AR](screenshots/walkthrough/ar_supply.jpg) |
| `/customers` | ✅ | ✅ | 3,510 | rtl | [EN](screenshots/walkthrough/en_customers.jpg) · [AR](screenshots/walkthrough/ar_customers.jpg) |
| `/products` | ✅ | ✅ | 3,469 | rtl | [EN](screenshots/walkthrough/en_products.jpg) · [AR](screenshots/walkthrough/ar_products.jpg) |
| `/products/P037` | ✅ | ✅ | 1,136 | rtl | [EN](screenshots/walkthrough/en_products_P037.jpg) · [AR](screenshots/walkthrough/ar_products_P037.jpg) |
| `/merchandising` | ✅ | ✅ | 5,001 | rtl | [EN](screenshots/walkthrough/en_merchandising.jpg) · [AR](screenshots/walkthrough/ar_merchandising.jpg) |
| `/inventory` | ✅ | ✅ | 7,545 | rtl | [EN](screenshots/walkthrough/en_inventory.jpg) · [AR](screenshots/walkthrough/ar_inventory.jpg) |
| `/marketing` | ✅ | ✅ | 3,801 | rtl | [EN](screenshots/walkthrough/en_marketing.jpg) · [AR](screenshots/walkthrough/ar_marketing.jpg) |
| `/suppliers` | ✅ | ✅ | 3,152 | rtl | [EN](screenshots/walkthrough/en_suppliers.jpg) · [AR](screenshots/walkthrough/ar_suppliers.jpg) |
| `/operations` | ✅ | ✅ | 1,783 | rtl | [EN](screenshots/walkthrough/en_operations.jpg) · [AR](screenshots/walkthrough/ar_operations.jpg) |
| `/quality` | ✅ | ✅ | 2,880 | rtl | [EN](screenshots/walkthrough/en_quality.jpg) · [AR](screenshots/walkthrough/ar_quality.jpg) |
| `/value` | ✅ | ✅ | 1,264 | rtl | [EN](screenshots/walkthrough/en_value.jpg) · [AR](screenshots/walkthrough/ar_value.jpg) |
| `/data` | ✅ | ✅ | 2,416 | rtl | [EN](screenshots/walkthrough/en_data.jpg) · [AR](screenshots/walkthrough/ar_data.jpg) |
| `/users` | ✅ | ✅ | 718 | rtl | [EN](screenshots/walkthrough/en_users.jpg) · [AR](screenshots/walkthrough/ar_users.jpg) |
| `/account` | ✅ | ✅ | 715 | rtl | [EN](screenshots/walkthrough/en_account.jpg) · [AR](screenshots/walkthrough/ar_account.jpg) |
| `/method` | ✅ | ✅ | 4,979 | rtl | [EN](screenshots/walkthrough/en_method.jpg) · [AR](screenshots/walkthrough/ar_method.jpg) |

## What this does and does not prove
- Proves: every route renders with real data in both languages, the Arabic layout is right-to-left, and no request fails for the CEO role.
- Does **not** prove: other roles (Store, Marketing, Production, Analyst) see the right things in the browser (role rules are covered by backend tests, not walked here); phone/tablet layouts; clicking every button (approving a plan, recording an outcome, importing data); Firefox/Safari; Docker (no Docker daemon was available where this was run; `docker compose config` validates, the stack itself was not started).
- Text that comes from the engines (titles such as "Investigate supplier: ...", evidence statements, product names) is generated in English by the backend and is not translated; the interface around it is.
- The data is `Modeled/Anonymized Training Data`: numbers shown are estimates on training data, not confirmed business results.

Re-run: start the stack, then `python ops/smoke.py --base http://localhost:3000 --import` for the API checks. The screenshots are JPEG q45 full-page (EN) and first screen (AR).
