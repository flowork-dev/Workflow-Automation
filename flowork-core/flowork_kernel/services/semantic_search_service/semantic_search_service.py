#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\semantic_search_service\semantic_search_service.py JUMLAH BARIS 122 
#######################################################################

import threading
from ..base_service import BaseService
import os
import json
import time
try:
    from sentence_transformers import SentenceTransformer
    from sentence_transformers.util import cos_sim
    import torch # ADDED: Import the core torch library
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
class SemanticSearchService(BaseService):
    """
    The 'brain' behind semantic search. It scans all components, creates
    vector embeddings for them, and provides a method to find the most
    relevant components for a given text query.
    [FIXED] Solved a race condition by subscribing to the event on the main thread
    before starting the background model loading.
    [FIXED V2] Added missing 'import time'.
    [FIXED V3] Correctly stack tensors before comparison to fix ValueError.
    """
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.logger = self.kernel.write_to_log
        self.model = None
        self.component_embeddings = {} # {'modules': [{'id': ..., 'embedding': ...}]}
        self.is_ready = False
        self.lock = threading.Lock()
    def start(self):
        """
        Loads the AI model and builds the initial embedding index in a background thread.
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            self.logger("Library 'sentence-transformers' not found. Semantic Search will be disabled.", "ERROR")
            self.kernel.write_to_log("Please run 'pip install sentence-transformers' to enable this feature.", "ERROR")
            return
        self.logger("Semantic Search Service is starting...", "INFO")
        event_bus = self.kernel.get_service("event_bus")
        if event_bus:
            event_bus.subscribe("event_all_services_started", f"{self.service_id}_builder", self.build_index)
        threading.Thread(target=self._initialize_model, daemon=True).start()
    def _initialize_model(self):
        """Loads the AI model in the background."""
        try:
            self.logger("Loading sentence transformer model... (This may take a moment)", "INFO")
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            self.logger("Sentence transformer model loaded successfully.", "SUCCESS")
        except Exception as e:
            self.logger(f"Failed to initialize Semantic Search Service model: {e}", "CRITICAL")
            self.is_ready = False
    def build_index(self, event_data=None):
        """
        Scans all components and creates vector embeddings for their metadata.
        This method is now safely called by the event bus after all modules are loaded.
        """
        while not self.model:
            time.sleep(0.5)
        self.logger("Building semantic search index...", "INFO")
        module_manager = self.kernel.get_service("module_manager_service")
        widget_manager = self.kernel.get_service("widget_manager_service")
        component_sources = {
            "modules": module_manager.loaded_modules if module_manager else {},
            "plugins": module_manager.loaded_modules if module_manager else {},
            "widgets": widget_manager.loaded_widgets if widget_manager else {}
        }
        with self.lock:
            self.component_embeddings.clear()
            for comp_type, components in component_sources.items():
                self.component_embeddings[comp_type] = []
                texts_to_encode = []
                component_ids = []
                for comp_id, data in components.items():
                    installed_as = data.get('installed_as')
                    if comp_type == 'modules' and installed_as != 'module':
                        continue
                    if comp_type == 'plugins' and installed_as != 'plugin':
                        continue
                    manifest = data.get('manifest', {})
                    searchable_text = f"Name: {manifest.get('name', '')}. Description: {manifest.get('description', '')}. ID: {comp_id}"
                    texts_to_encode.append(searchable_text)
                    component_ids.append(comp_id)
                if texts_to_encode:
                    embeddings = self.model.encode(texts_to_encode, convert_to_tensor=True)
                    for i, comp_id in enumerate(component_ids):
                        self.component_embeddings[comp_type].append({
                            'id': comp_id,
                            'embedding': embeddings[i]
                        })
            self.is_ready = True
            self.logger("Semantic search index built successfully.", "SUCCESS")
            event_bus = self.kernel.get_service("event_bus")
            if event_bus:
                event_bus.publish("SEMANTIC_INDEX_BUILT", {"status": "ready"})
    def search(self, query: str, component_type: str, top_k: int = 10) -> list[str]:
        """
        Finds the most relevant components for a given query.
        Returns a ranked list of component IDs.
        """
        if not self.is_ready or not self.model:
            return []
        with self.lock:
            if component_type not in self.component_embeddings or not self.component_embeddings[component_type]:
                return []
            corpus = self.component_embeddings[component_type]
            corpus_embeddings = [item['embedding'] for item in corpus]
            corpus_tensor = torch.stack(corpus_embeddings)
            query_embedding = self.model.encode(query, convert_to_tensor=True)
            cos_scores = cos_sim(query_embedding, corpus_tensor)[0]
            top_results = cos_scores.topk(min(top_k, len(corpus)), largest=True)
            ranked_ids = []
            for score, idx in zip(top_results[0], top_results[1]):
                if score > 0.25:
                    ranked_ids.append(corpus[idx]['id'])
            return ranked_ids
