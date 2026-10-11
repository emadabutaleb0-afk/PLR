"""Row- and file-level validation. Never raises on bad data: invalid rows are quarantined with a plain-language reason."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
import pandas as pd
from app.ingestion.specs import FileSpec

MIN_DATE = pd.Timestamp("2000-01-01")


@dataclass
class ValidationResult:
    file: str
    fatal: str | None = None
    rows_read: int = 0
    clean: pd.DataFrame | None = None
    quarantine: list[dict] = field(default_factory=list)
    issues: list[dict] = field(default_factory=list)
    null_rate: float = 0.0
    duplicate_rate: float = 0.0
    latest_date: str | None = None
    column_null_rates: dict = field(default_factory=dict)
    data_class: str | None = None

    @property
    def rows_clean(self) -> int:
        return 0 if self.clean is None else len(self.clean)

    quarantine_all: int = 0

    @property
    def rows_rejected(self) -> int:
        return self.quarantine_all


def read_csv(path) -> pd.DataFrame:
    # keep_default_na=False: the literal word "None" is a REAL category (e.g. Defect_Type) and must not become NaN
    df = pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""], encoding="utf-8-sig",
                     on_bad_lines="skip", skipinitialspace=True)
    df.columns = [c.strip().lstrip("\ufeff") for c in df.columns]
    return df


def _issue(res, rule, sev, count, msg, sample=None):
    res.issues.append(dict(rule=rule, severity=sev, row_count=int(count), message=msg,
                           sample=[int(x) for x in (sample or [])][:5]))


def validate_frame(spec: FileSpec, raw: pd.DataFrame, ref_keys: dict[str, set], today: date | None = None,
                   stale_days: int = 45, max_quarantine: int = 2000) -> ValidationResult:
    today = today or date.today()
    res = ValidationResult(file=spec.file, rows_read=len(raw))

    missing_req = [c for c in spec.required if c not in raw.columns]
    if missing_req:
        res.fatal = f"{spec.file} is missing required column(s): {', '.join(missing_req)}"
        return res
    df = raw.copy()
    for c in spec.cols:
        if c not in df.columns:
            df[c] = None
            _issue(res, "missing_optional_column", "warn", len(df), f"{spec.file} has no column {c}; it was left empty")
    extra = [c for c in df.columns if c not in spec.cols]
    if extra:
        _issue(res, "unknown_columns", "warn", 0, f"Ignored unrecognised column(s): {', '.join(extra)}")
    df = df[list(spec.cols)]
    for c, t in spec.cols.items():
        if t == "s":
            df[c] = df[c].where(df[c].isna(), df[c].astype(str).str.strip())
            df[c] = df[c].replace("", None)

    if "Data_Class" in df.columns and len(df):
        res.data_class = str(df["Data_Class"].dropna().mode().iloc[0]) if df["Data_Class"].notna().any() else None
    if res.rows_read == 0:
        res.clean = df.iloc[0:0]
        _issue(res, "empty_file", "warn", 0, f"{spec.file} contains no data rows")
        return res

    reasons = pd.Series("", index=df.index, dtype=object)
    counts: dict[str, tuple[str, int, list]] = {}

    def flag(mask: pd.Series, rule: str, msg: str):
        mask = mask.fillna(False).astype(bool)
        new = mask & (reasons == "")
        reasons[new] = msg
        n = int(new.sum())
        if n:
            counts[rule] = (msg, n, [int(i) + 2 for i in df.index[new][:5]])

    # --- type coercion (invalid values quarantine the row; blanks handled by required check)
    typed = df.copy()
    ts_max = None
    for c, t in spec.cols.items():
        nn = df[c].notna()
        if t in ("i", "f"):
            v = pd.to_numeric(df[c], errors="coerce")
            flag(nn & v.isna(), f"invalid_number_{c}", f"{c} is not a valid number")
            typed[c] = v
        elif t == "d":
            v = pd.to_datetime(df[c], format="ISO8601", errors="coerce")
            flag(nn & v.isna(), f"invalid_date_{c}", f"{c} is not a valid date (expected YYYY-MM-DD)")
            flag(v.notna() & ((v < MIN_DATE) | (v > pd.Timestamp(today) + timedelta(days=366))),
                 f"implausible_date_{c}", f"{c} is outside the plausible date range")
            typed[c] = v
        elif t == "yn":
            low = df[c].astype(str).str.lower()
            v = low.map({"yes": True, "no": False, "true": True, "false": False, "1": True, "0": False})
            flag(nn & v.isna(), f"invalid_flag_{c}", f"{c} must be Yes or No")
            typed[c] = v.astype(object).where(v.notna(), None)
    for c in spec.required:
        flag(df[c].isna(), f"missing_{c}", f"required value {c} is empty")

    # --- primary key duplicates (keep first occurrence)
    pk = list(spec.pk)
    dups = typed.duplicated(subset=pk, keep="first") & typed[pk].notna().all(axis=1)
    res.duplicate_rate = float(dups.mean())
    flag(dups, "duplicate_key", f"duplicate primary key ({', '.join(pk)})")

    # --- foreign keys against parent tables (real relationships only)
    for col, rt, rc in spec.fks:
        keys = ref_keys.get(rt)
        if keys is None:
            _issue(res, "fk_unchecked", "warn", 0, f"{spec.file}: parent table {rt} unavailable, {col} not checked")
            continue
        flag(typed[col].notna() & ~typed[col].isin(keys), f"invalid_fk_{col}",
             f"{col} does not exist in {rt} (invalid reference)")

    # --- business rules
    for r in spec.rules:
        try:
            mask = r.check(typed).fillna(False).astype(bool)
        except Exception as e:  # a rule must never crash an import
            _issue(res, r.name, "warn", 0, f"rule {r.name} could not run: {type(e).__name__}")
            continue
        if r.severity == "reject":
            flag(mask, r.name, r.message)
        elif mask.any():
            _issue(res, r.name, "warn", mask.sum(), r.message, [int(i) + 2 for i in df.index[mask][:5]])

    # --- null rate on required columns, staleness
    res.null_rate = float(df[spec.required].isna().mean().mean())
    res.column_null_rates = {c: round(float(df[c].isna().mean()), 4) for c in spec.cols if df[c].isna().any()}
    if spec.date_col and spec.date_col in typed and typed[spec.date_col].notna().any():
        mx = typed[spec.date_col].max()
        res.latest_date = mx.date().isoformat()
        age = (pd.Timestamp(today) - mx).days
        if age > stale_days:
            _issue(res, "stale_data", "warn", 0, f"{spec.file} is stale: newest {spec.date_col} is {res.latest_date} ({age} days old)")

    for rule, (msg, n, sample) in counts.items():
        _issue(res, rule, "reject", n, msg, sample)

    bad = reasons != ""
    for idx in df.index[bad][:max_quarantine]:
        res.quarantine.append(dict(row_number=int(idx) + 2, reason=reasons[idx],
                                   raw={k: (None if pd.isna(v) else str(v))[:120] if v is not None and not pd.isna(v) else None
                                        for k, v in list(raw.loc[idx].items())[:30]}))
    res.quarantine_all = int(bad.sum())
    res.clean = typed[~bad].reset_index(drop=True)
    return res
