"""dashboard/utils/__init__.py — public re-exports."""
from .bigquery_client import (  # noqa: F401
    get_gdp_trends,
    get_unemployment,
    get_energy_intensity,
    get_composite_index,
    get_country_latest,
    get_anomaly_alerts,
)
