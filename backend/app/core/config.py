from functools import lru_cache
from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> parents[3] is the project root, parents[2] is backend/
ROOT = Path(__file__).resolve().parents[3]
BACKEND = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # .env is looked up in backend/ first, then in the project root, so it works wherever the server is started from
    model_config = SettingsConfigDict(env_file=(str(ROOT / ".env"), str(BACKEND / ".env")), extra="ignore")
    environment: str = "development"
    database_url: str = f"sqlite:///{(BACKEND / 'merchbrain.db').as_posix()}"
    redis_url: str | None = None  # None -> in-process cache + threaded jobs
    data_directory: str = ""   # empty -> auto-detect (see data_dir property)
    company_name: str = ""   # optional override; defaults to data-detected name or 'Business Gate'
    model_directory: str = str(BACKEND / "models_store")
    secret_key: str = "dev-only-secret-change-me-dev-only-secret"
    access_token_minutes: int = 30
    refresh_token_days: int = 7
    cors_origins: str = "http://localhost:3000"
    rate_limit_per_minute: int = 240
    bootstrap_admin_email: str = "admin"
    bootstrap_admin_password: str = "change-me-now"
    stale_data_days: int = 45
    celery_enabled: bool = False
    auto_import_on_start: bool = True   # first start with an empty database -> import the company CSVs by itself
    # Business parameters (assumptions are explicit, configurable and shown in evidence; not company facts)
    target_cover_days: int = 45
    dead_cover_days: int = 180
    transfer_cost_per_unit_egp: float = 0.0   # unavailable in the data -> configurable, default 0
    margin_floor_pct: float = 0.05            # never recommend a discount that pushes margin below this
    capital_cost_annual_pct: float = 0.20     # holding-cost assumption used only in markdown optimisation
    delay_impact_pass_through: float = 0.05   # share of a late-material day assumed to hit production (assumption)
    planning_horizon_days: int = 30
    outcome_window_days: int = 28            # before/after window used to measure an executed decision
    block_stale_approvals: bool = True       # refuse approvals while the newest business data is older than STALE_DATA_DAYS (unless acknowledged)
    decision_budget_egp: float | None = None  # optional cash cap on replenishment spend inside a decision plan (None = unconstrained; unknown company figure)
    max_actions_per_department: int = 8       # how many actions one department can absorb per plan (assumption, configurable)
    discount_comfort_pct: float = 0.10        # discount depth above this in Retail/Online is counted as 'discount leakage' (assumption, configurable)
    assumed_discount_lift_per_10pp: float = 0.30  # used ONLY because the data shows no measurable price response

    @field_validator("decision_budget_egp", mode="before")
    @classmethod
    def _blank_budget_means_none(cls, v):
        """`DECISION_BUDGET_EGP=` (empty) in a .env file must mean 'no cap', not a crash."""
        return None if isinstance(v, str) and not v.strip() else v

    def production_problems(self) -> list[str]:
        """Settings that must never reach production. Empty list = safe."""
        bad = []
        if self.secret_key.startswith("dev-only") or len(self.secret_key) < 32:
            bad.append("SECRET_KEY is a default or shorter than 32 characters")
        if self.bootstrap_admin_password in ("change-me-now", "") or len(self.bootstrap_admin_password) < 12:
            bad.append("BOOTSTRAP_ADMIN_PASSWORD is a default or shorter than 12 characters")
        if "*" in self.cors_list:
            bad.append("CORS_ORIGINS allows every origin")
        return bad

    @property
    def data_dir(self) -> str:
        """Company data folder. Uses DATA_DIRECTORY when it exists, otherwise looks in the usual places so a missing/Docker-only path never leaves the app empty."""
        cands = [self.data_directory] if self.data_directory else []
        cands += [str(ROOT / "data" / "private"), str(BACKEND / "data" / "private"), str(Path.cwd() / "data" / "private"), str(Path.cwd().parent / "data" / "private")]
        for c in cands:
            if c and Path(c).is_dir() and any(Path(c).glob("*.csv")):
                return c
        return cands[0] if cands else str(ROOT / "data" / "private")

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
