#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\utils\tracing_setup.py JUMLAH BARIS 26 
#######################################################################

import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
def setup_tracing(service_name="flowork-core"):
    """
    Mengkonfigurasi OpenTelemetry untuk tracing.
    (PERBAIKAN) Hanya aktif jika environment variable diset.
    (MODIFIKASI) Fitur dinonaktifkan permanen sesuai permintaan untuk menghapus Jaeger.
    """
    return trace.get_tracer_provider().get_tracer(service_name)
def get_trace_context_from_headers(headers):
    """
    Mengekstrak konteks trace dari HTTP headers.
    (MODIFIKASI) Dinonaktifkan dan selalu mengembalikan None.
    """
    return None
