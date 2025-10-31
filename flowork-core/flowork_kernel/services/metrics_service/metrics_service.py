#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\metrics_service\metrics_service.py JUMLAH BARIS 65 
#######################################################################

import threading
import time
import psutil
import os
from ..base_service import BaseService
from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
class MetricsService(BaseService):
    """
    Service terpusat untuk mengumpulkan dan menyajikan metrik aplikasi
    dalam format yang kompatibel dengan Prometheus.
    """
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.process = psutil.Process(os.getpid())
        for coll in list(REGISTRY._collector_to_names.keys()):
            REGISTRY.unregister(coll)
        self.WORKFLOWS_TOTAL = Counter(
            "flowork_workflows_processed_total",
            "Total number of workflows processed",
            [
                "status"
            ],  # (COMMENT) Bisa di-filter berdasarkan status: 'succeeded' atau 'failed'
        )
        self.WORKFLOW_DURATION = Histogram(
            "flowork_workflow_duration_seconds",
            "Histogram for the duration of workflow execution",
        )
        self.CPU_USAGE = Gauge(
            "flowork_cpu_usage_percent", "Current CPU usage of the Core Engine process"
        )
        self.MEMORY_USAGE_MB = Gauge(
            "flowork_memory_usage_mb",
            "Current memory usage (RSS) of the Core Engine process",
        )
        self.update_thread = None
        self.stop_event = threading.Event()
    def start(self):
        """Memulai thread background untuk update metrik sistem (CPU, RAM)."""
        self.update_thread = threading.Thread(
            target=self._update_system_metrics, daemon=True
        )
        self.update_thread.start()
        self.logger("MetricsService: Background monitoring started.", "SUCCESS")
    def stop(self):
        """Menghentikan thread background."""
        self.stop_event.set()
        if self.update_thread:
            self.update_thread.join(timeout=2)
        self.logger("MetricsService: Background monitoring stopped.", "INFO")
    def _update_system_metrics(self):
        """Loop yang berjalan di background untuk mengupdate metrik secara periodik."""
        while not self.stop_event.is_set():
            self.CPU_USAGE.set(self.process.cpu_percent())
            self.MEMORY_USAGE_MB.set(self.process.memory_info().rss / (1024 * 1024))
            time.sleep(5)
    def serve_metrics(self):
        """Menghasilkan output teks mentah untuk di-scrape oleh Prometheus."""
        return generate_latest(REGISTRY)
