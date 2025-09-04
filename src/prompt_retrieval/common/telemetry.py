# src/prompt_retrieval/telemetry.py
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any

from opentelemetry import metrics, trace
from opentelemetry.metrics import Meter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import Tracer

# Azure Monitor (Application Insights) OpenTelemetry exporters
# NOTE: These are the official exporters for Azure Monitor + OTel (Python). They
# will use APPLICATIONINSIGHTS_CONNECTION_STRING if you do not pass one directly.
# https://pypi.org/project/azure-monitor-opentelemetry-exporter/
try:
    from azure.monitor.opentelemetry.exporter import (
        AzureMonitorMetricExporter,
        # AzureMonitorLogExporter  # (logs exporter may be experimental)
        AzureMonitorTraceExporter,
    )
    _HAS_AZURE_EXPORTERS = True
except Exception:
    _HAS_AZURE_EXPORTERS = False


class TelemetryService:
    """
    Abstraction over Python logging + OpenTelemetry with Azure Monitor (App Insights).

    - Always provides Python logger methods (info/debug/warning/error/exception).
    - Provides tracing via OpenTelemetry (spans).
    - Provides a Counter metric to record 'matched questions per assessment'.

    Azure Monitor export is enabled if 'APPLICATIONINSIGHTS_CONNECTION_STRING' is set
    and azure-monitor-opentelemetry-exporter is installed. Otherwise, falls back to
    console exporters for local/dev to avoid hard failures.

    Connection string reference:
      https://learn.microsoft.com/azure/azure-monitor/app/connection-strings
    Exporters reference:
      https://pypi.org/project/azure-monitor-opentelemetry-exporter/
    """

    def __init__(
        self,
        service_name: str = "prompt-retrieval",
        service_version: str = "0.1.0",
        logger: logging.Logger | None = None,
        enable_console_exporters_when_no_ai: bool = True,
        metric_export_interval_millis: int = 15000,
    ) -> None:
        self._logger = logger or logging.getLogger(service_name)
        self._logger.propagate = True

        connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
        resource = Resource.create({"service.name": service_name, "service.version": service_version})

        # Check if we're running in a test environment
        is_testing = (
            os.getenv("PYTEST_CURRENT_TEST") is not None or
            "pytest" in service_name.lower()
        )

        # ---------- Tracing ----------
        tracer_provider = TracerProvider(resource=resource)
        if _HAS_AZURE_EXPORTERS and connection_string and not is_testing:
            tracer_exporter = AzureMonitorTraceExporter(connection_string=connection_string)
            tracer_provider.add_span_processor(BatchSpanProcessor(tracer_exporter))
        elif enable_console_exporters_when_no_ai and not is_testing:
            tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        trace.set_tracer_provider(tracer_provider)
        self._tracer: Tracer = trace.get_tracer(__name__, service_version)

        # ---------- Metrics ----------
        metric_readers = []
        if _HAS_AZURE_EXPORTERS and connection_string and not is_testing:
            metric_exporter = AzureMonitorMetricExporter(connection_string=connection_string)
            metric_readers.append(
                PeriodicExportingMetricReader(
                    exporter=metric_exporter,
                    export_interval_millis=metric_export_interval_millis,
                )
            )
        elif enable_console_exporters_when_no_ai and not is_testing:
            metric_readers.append(
                PeriodicExportingMetricReader(
                    exporter=ConsoleMetricExporter(),
                    export_interval_millis=metric_export_interval_millis,
                )
            )

        meter_provider = MeterProvider(resource=resource, metric_readers=metric_readers)
        metrics.set_meter_provider(meter_provider)
        self._meter: Meter = metrics.get_meter(__name__, service_version)

        # Counter: matched_questions_total (by assessment_template_id)
        self._matched_counter = self._meter.create_counter(
            name="matched_questions_total",
            description="Number of matched questions per assessment",
            unit="1",
        )

    # ------------- Python logger facade -------------

    def debug(self, msg: str, *args, **kwargs) -> None:
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs) -> None:
        self._logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs) -> None:
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs) -> None:
        self._logger.error(msg, *args, **kwargs)

    def exception(self, msg: str, *args, **kwargs) -> None:
        self._logger.exception(msg, *args, **kwargs)

    # ------------- Tracing helpers -------------

    @contextmanager
    def start_span(self, name: str, attributes: dict[str, Any] | None = None):
        """Context manager to create a span around operations."""
        with self._tracer.start_as_current_span(name) as span:
            if attributes:
                for k, v in attributes.items():
                    span.set_attribute(k, v)
            yield span

    # ------------- Metrics -------------

    def record_matched_questions(self, assessment_template_id: str, count: int) -> None:
        """
        Increments the matched questions counter for a given assessment template.
        """
        attributes = {"assessment_template_id": assessment_template_id}
        # OpenTelemetry Metrics API: Counter.add(value, attributes)
        # https://opentelemetry.io/docs/languages/python/
        self._matched_counter.add(count, attributes)

    # ------------- Cleanup -------------

    def shutdown(self) -> None:
        """
        Flush and shutdown providers to ensure clean exit.
        """
        try:
            # Force flush any pending traces and metrics
            tracer_provider = trace.get_tracer_provider()
            if hasattr(tracer_provider, 'force_flush'):
                tracer_provider.force_flush(timeout_millis=5000)
            
            meter_provider = metrics.get_meter_provider()
            if hasattr(meter_provider, 'force_flush'):
                meter_provider.force_flush(timeout_millis=5000)
            
            # Shutdown providers
            if hasattr(tracer_provider, 'shutdown'):
                tracer_provider.shutdown()
            if hasattr(meter_provider, 'shutdown'):
                meter_provider.shutdown()
        except Exception as e:
            # Log error but don't raise to avoid disrupting application shutdown
            self._logger.debug(f"Error during telemetry shutdown: {e}")