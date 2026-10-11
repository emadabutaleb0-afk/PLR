# Decision engines: method, assumptions, limits
Effective cover = min(Days_of_Cover as supplied, stock ÷ expected demand). Expected demand = demand forecast, guarded to ≤ 2× the larger of current pace and last year's same-season pace.

| Engine | Method | Estimate basis / limit |
|---|---|---|
| Product Action | Per product×location rules combining stockout risk, dead-stock risk, transfer plan, markdown, quality, yoy growth, margin | confidence = transparent score (signal strength, model agreement, history, volatility) |
| Dead-Stock Rescue | excess = stock − 90-day expected demand; risk from LightGBM + cover rule; options TRANSFER / DISCOUNT / MARKETING_SUPPORT / STOP_REPLENISHMENT / PHASE_OUT | recoverable = expected loss avoided by the primary action |
| Size Curve | recent (180d) vs prior-12-month sales mix, return/size-fit rates, shrinkage to baseline, largest-remainder allocation of the reorder need | **current stock by size unavailable** |
| Markdown | SciPy bounded optimiser; margin floor enforced; leftover stock charged holding cost + p(dead)×cost | price response not measurable in the data → lift per 10pp is an explicit assumption |
| Campaign collision | live/recent campaigns vs consumer-channel cover, production issues, quality, overstock without support | wasted spend = spend × share of period beyond stock cover (estimate) |
| Margin Erosion | exact additive decomposition of Δ contribution (volume, discount, COGS, price/mix, returns, quality, rework, production rejects, campaign) last 90d vs previous 90d; Margin Health Score 0–100 (weights shown) | recoverable = restoring the biggest negative driver to last quarter's level |
| Supplier True Cost | **Observed** (rejected material value + spend above material median price) kept separate from **Estimated risk** (late days / rejected units × exposed profit × pass-through) | pass-through default 5% = assumption |
| Quality Impact | Pareto, root cause, stage, product cost of poor quality, Spearman associations (lag 0/1) | associations only; "no reliable relationship" is reported as such |
| Recovery Priority | score = value × confidence × urgency multiplier, log-scaled 0–100, one issue per entity | — |
| Lost Sales | stockout days × trailing-90d daily sales × actual selling price | conservative (daily sales is depressed during stockouts) |
| Inventory Productivity | GP per unit held per day; annualised GMROI; Fast-profitable / Slow-capital-trapping classes | — |
| Product Strategy | 8 scores (demand, margin, inventory, quality, production, supplier, marketing, customer) → SCALE/MAINTAIN/FIX/RELOCATE/DISCOUNT/STOP_REPLENISHMENT/PHASE_OUT with the rule that fired | percentile-based; no ML (59 products) |

Configurable parameters (`.env`): TARGET_COVER_DAYS, DEAD_COVER_DAYS, TRANSFER_COST_PER_UNIT_EGP, MARGIN_FLOOR_PCT, CAPITAL_COST_ANNUAL_PCT, DELAY_IMPACT_PASS_THROUGH, ASSUMED_DISCOUNT_LIFT_PER_10PP.

## Commercial intelligence engines (added)
| Engine | Method | Basis / limit |
|---|---|---|
| Profit Leakage | 12-month additive view of 5 leaks: stockouts (**estimate**), discounts above the comfort band (**exposure**, assumes no volume lift), QC loss (**recorded**), returns (**recorded**), production + print waste (**estimate**) | Factory volumes are ~3.5x the units in the sales ledger, so quality/production leakage is attributed per product with min(1, sold ÷ produced); unscaled values are shown. QC losses and production rejects may overlap and are never netted |
| Supply Readiness | forecast demand → inventory gap → production need (grossed up for reject rate) → BOM material need → supplier risk score (late rate 45%, delay 30%, rejects 25%) | **No raw-material stock exists in the data**: it reports requirement and supplier reliability, not a physical shortage |
| Channel Allocation | greedy fill by gross profit per unit (exactly optimal for this linear problem): lead-time demand + safety first, then horizon demand, excess parked by demand | 3 selling locations only (Retail / Online / Wholesale); no branch-transfer network is invented. Wholesale is contract-driven: confirm commitments first |
| Discount Intelligence | per-channel discount bands (GP per unit, margin, break-even lift) + volume test within product and month (two-way fixed effects, 95% range) | Association, not causal elasticity. In Retail/Online the data shows no measurable lift, so the engine says so rather than assuming one |
| Command Center | 6 headline numbers + 5 actions (revenue, margin, dead stock, supply, leakage) | Values labelled as estimate, exposure or dependency, never as guaranteed savings |

New parameter: `DISCOUNT_COMFORT_PCT` (default 0.10).

## Round 2 additions
| Feature | What it does | Honest result on the supplied data |
|---|---|---|
| Forecast signals | Demand models can use advertising (spend, clicks, attributed orders, discount, lags) and website momentum (sessions, conversion, add-to-cart, checkout). For each horizon the model with signals is used **only if it beats the base model by 2% on the time-based validation window**; both errors are stored in the model registry (`wape_base_features`, `wape_with_signals`, `signals_used`) | On the training data the signals changed the error by under 1%, so they were **not** switched on. On real client data they may help; the choice is automatic |
| What-if Scenarios | Discount change, produce/order more units, material price change; each lists its assumptions. Discount volume lift defaults to 0% because the data shows none | Uses the demand pace already forecast; no hidden elasticity |
| Weekly report | PDF with the six headline numbers, five actions, leakage, supply risks and discount finding (`/api/v1/commercial/weekly-report.pdf`, button on the Command Center) | English only (the PDF font has no Arabic shaping); Arabic product names are omitted from it. Not emailed automatically: that needs SMTP settings |

## Round 3 additions
| Feature | What it does | Honest result on the supplied data |
|---|---|---|
| Customer Intelligence | Each customer is judged against their own buying rhythm (days since last invoice ÷ their median gap): Active / Slipping / Lapsed / New / One-time; profit concentration; overdue accounts to contact; acquisition source; service CSAT | Wholesale accounts bring about 65% of profit; about 748 wholesale accounts are overdue. Acquisition channels behave almost identically (repeat rate within 2 points), so source does not predict value. CSAT fell from 4.13 to 3.87 in the last 90 days |
| Downtime vs delays | Monthly correlation of unplanned downtime with production delay, and stage-by-stage comparison | Correlation is about 0.08: downtime does not explain delays. Printing has the most downtime but is the least frequent bottleneck; Sewing causes the most delay |
| How numbers are calculated | One page, EN + AR: what each big number means, how it is built, the data used and what it cannot tell you | |
| Demo Story | Six full-screen steps (question, leakage, what's next, actions, learnings, try it and what we do not claim); arrow keys work | |
