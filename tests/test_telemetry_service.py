# import os
# import types
# from contextlib import contextmanager

# import pytest

# from prompt_retrieval.telemetry import TelemetryService
# import prompt_retrieval.telemetry as telemetry_mod


# # -----------------------
# # Utilities / Fakes
# # -----------------------

# class DummyCounter:
#     def __init__(self):
#         self.calls = []

#     def add(self, value, attributes=None):
#         self.calls.append((value, attributes or {}))


# class FakeMetricReader:
#     """Fake replacement for PeriodicExportingMetricReader that records the exporter type."""
#     constructed = []

#     def __init__(self, exporter, export_interval_millis=15000):
#         # record the class name to assert in tests
#         self.exporter = exporter
#         FakeMetricReader.constructed.append(type(exporter).__name__)

#     def __repr__(self):
#         return f"<FakeMetricReader exporter={type(self.exporter).__name__}>"


# class FakeSpanProcessor:
#     """Fake replacement for BatchSpanProcessor that records exporter type."""
#     constructed = []

#     def __init__(self, exporter):
#         FakeSpanProcessor.constructed.append(type(exporter).__name__)
#         self.exporter = exporter


# class FakeTracer:
#     def __init__(self):
#         self.started = []

#     @contextmanager
#     def start_as_current_span(self, name):
#         self.started.append({"name": name, "attributes": {}})
#         # Provide an object that can accept set_attribute calls if needed
#         class _Span:
#             def set_attribute(self, k, v):
#                 self_attr = telemetry_mod.trace.get_current_span()
#                 # no-op in tests; we only verify that our wrapper was invoked
#                 return None

#         yield _Span()


# class FakeAzureMonitorMetricExporter:
#     pass


# class FakeAzureMonitorTraceExporter:
#     pass


# class FakeConsoleMetricExporter:
#     pass


# # -----------------------
# # Fixtures
# # -----------------------

# @pytest.fixture(autouse=True)
# def clear_env(monkeypatch):
#     # Ensure we control the presence/absence of the App Insights connection string per-test
#     if "APPLICATIONINSIGHTS_CONNECTION_STRING" in os.environ:
#         monkeypatch.delenv("APPLICATIONINSIGHTS_CONNECTION_STRING", raising=False)
#     yield


# # -----------------------
# # Tests
# # -----------------------

# def test_logger_methods_delegate(monkeypatch):
#     """Ensure logger methods delegate to the injected logger."""
#     class MockLogger:
#         def __init__(self):
#             self.calls = []

#         def debug(self, msg, *a, **k): self.calls.append(("debug", msg))
#         def info(self, msg, *a, **k): self.calls.append(("info", msg))
#         def warning(self, msg, *a, **k): self.calls.append(("warning", msg))
#         def error(self, msg, *a, **k): self.calls.append(("error", msg))
#         def exception(self, msg, *a, **k): self.calls.append(("exception", msg))

#     mock_logger = MockLogger()

#     # Avoid constructing real exporters by replacing readers/exporters with no-ops
#     monkeypatch.setattr(telemetry_mod, "PeriodicExportingMetricReader", FakeMetricReader)
#     monkeypatch.setattr(telemetry_mod, "ConsoleMetricExporter", FakeConsoleMetricExporter)

#     svc = TelemetryService(logger=mock_logger, enable_console_exporters_when_no_ai=True)

#     svc.debug("d")
#     svc.info("i")
#     svc.warning("w")
#     svc.error("e")
#     svc.exception("x")

#     kinds = [k for (k, _) in mock_logger.calls]
#     assert kinds == ["debug", "info", "warning", "error", "exception"]


# def test_record_matched_questions_calls_counter_add(monkeypatch):
#     """Ensure record_matched_questions increments the counter with proper attributes."""
#     # Patch the metric reader to avoid real exporters
#     monkeypatch.setattr(telemetry_mod, "PeriodicExportingMetricReader", FakeMetricReader)
#     monkeypatch.setattr(telemetry_mod, "ConsoleMetricExporter", FakeConsoleMetricExporter)

#     svc = TelemetryService(enable_console_exporters_when_no_ai=True)
#     dummy_counter = DummyCounter()
#     # Swap internal counter with our dummy to observe calls
#     svc._matched_counter = dummy_counter  # type: ignore[attr-defined]

#     svc.record_matched_questions("asm-123", 5)
#     assert dummy_counter.calls == [(5, {"assessment_template_id": "asm-123"})]


# def test_start_span_invokes_tracer(monkeypatch):
#     """Ensure start_span uses the tracer context manager."""
#     # Avoid exporters
#     monkeypatch.setattr(telemetry_mod, "PeriodicExportingMetricReader", FakeMetricReader)
#     monkeypatch.setattr(telemetry_mod, "ConsoleMetricExporter", FakeConsoleMetricExporter)

#     svc = TelemetryService(enable_console_exporters_when_no_ai=True)
#     fake_tracer = FakeTracer()
#     svc._tracer = fake_tracer  # type: ignore[attr-defined]

#     with svc.start_span("unit-span", {"k": "v"}):
#         # Inside the span; success means our tracer context manager ran without error
#         pass

#     assert len(fake_tracer.started) == 1
#     assert fake_tracer.started[0]["name"] == "unit-span"


# def test_initializes_console_exporters_when_no_connection_string(monkeypatch):
#     """When no APPLICATIONINSIGHTS_CONNECTION_STRING, TelemetryService uses Console exporters."""
#     # Force Azure exporters branch off (not installed)
#     monkeypatch.setattr(telemetry_mod, "_HAS_AZURE_EXPORTERS", False, raising=True)

#     # Replace exporter classes/readers with fakes and capture what was used
#     FakeMetricReader.constructed.clear()
#     monkeypatch.setattr(telemetry_mod, "PeriodicExportingMetricReader", FakeMetricReader, raising=True)
#     monkeypatch.setattr(telemetry_mod, "ConsoleMetricExporter", FakeConsoleMetricExporter, raising=True)

#     _ = TelemetryService(enable_console_exporters_when_no_ai=True)

#     # Expect our FakeMetricReader to be constructed with a ConsoleMetricExporter
#     assert "FakeConsoleMetricExporter" in FakeMetricReader.constructed


# @pytest.mark.skipif(not telemetry_mod._HAS_AZURE_EXPORTERS, reason="Azure Monitor exporters not installed")
# def test_uses_azure_exporters_when_connection_string_present(monkeypatch):
#     """
#     With APPLICATIONINSIGHTS_CONNECTION_STRING set and Azure exporters available,
#     ensure Azure exporters are wired for both traces and metrics.
#     """
#     # Set connection string in env
#     monkeypatch.setenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "InstrumentationKey=00000000-0000-0000-0000-000000000000")

#     # Swap Azure exporters with fakes to observe instantiation
#     monkeypatch.setattr(telemetry_mod, "AzureMonitorMetricExporter", FakeAzureMonitorMetricExporter, raising=True)
#     monkeypatch.setattr(telemetry_mod, "AzureMonitorTraceExporter", FakeAzureMonitorTraceExporter, raising=True)

#     # Capture which exporter class was given to BatchSpanProcessor (for TRACE)
#     FakeSpanProcessor.constructed.clear()
#     monkeypatch.setattr(telemetry_mod, "BatchSpanProcessor", FakeSpanProcessor, raising=True)

#     # Capture which exporter class was given to PeriodicExportingMetricReader (for METRICS)
#     FakeMetricReader.constructed.clear()
#     monkeypatch.setattr(telemetry_mod, "PeriodicExportingMetricReader", FakeMetricReader, raising=True)

#     svc = TelemetryService(enable_console_exporters_when_no_ai=False)

#     # Assert TRACE pipeline saw AzureMonitorTraceExporter
#     assert "FakeAzureMonitorTraceExporter" in FakeSpanProcessor.constructed

#     # Assert METRICS pipeline saw AzureMonitorMetricExporter
#     assert "FakeAzureMonitorMetricExporter" in FakeMetricReader.constructed

#     # Use the service to ensure nothing explodes
#     svc.info("telemetry wired with azure exporters")