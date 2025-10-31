#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\services\ai_analyzer_service\ai_analyzer_service.py JUMLAH BARIS 216 
#######################################################################

import os
import json
import threading
import re
import hashlib
import traceback
import sys
import subprocess
from ..base_service import BaseService
try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
class AIAnalyzerService(BaseService):
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.state_manager = self.kernel.get_service("state_manager")
        self.preset_manager = self.kernel.get_service("preset_manager_service")
        self.event_bus = self.kernel.get_service("event_bus")
        self.kernel.write_to_log("Service 'AIAnalyzerService' initialized.", "DEBUG")
    def start(self):
        self.kernel.write_to_log("AI Co-pilot (New Pattern Analyzer) is ready and waiting for events.", "SUCCESS")
    def stop(self):
        pass
    def request_analysis(self, context_id: str):
        analysis_thread = threading.Thread(target=self._run_analysis, args=(context_id,), daemon=True)
        analysis_thread.start()
    def _run_analysis(self, context_id: str):
        if not self.kernel.is_tier_sufficient('pro'):
            return
        if self.event_bus:
            self.event_bus.publish("AI_ANALYSIS_STARTED", {"message": "AI Co-pilot is analyzing..."})
        self.kernel.write_to_log(f"AI Co-pilot: Analysis request received for context '{context_id}'.", "INFO")
        try:
            preset_name = self.state_manager.get(f"tab_preset_map::{context_id}")
            if not preset_name or not self.preset_manager:
                return
            preset_data = self.preset_manager.get_preset_data(preset_name)
            if not preset_data: return
            active_master_ai_id = self.loc.get_setting("ai_model_for_text")
            logical_structure = {
                'nodes': [{k: v for k, v in node.items() if k not in ['x', 'y']} for node in preset_data.get('nodes', [])],
                'connections': preset_data.get('connections', [])
            }
            workflow_str = json.dumps(logical_structure, sort_keys=True) + str(active_master_ai_id)
            workflow_hash = hashlib.md5(workflow_str.encode('utf-8')).hexdigest()
            cache_key = f"ai_suggestion::{preset_name}::{workflow_hash}"
            cached_suggestions = self.state_manager.get(cache_key)
            if cached_suggestions is not None:
                is_cache_valid = False
                try:
                    json_matches = re.findall(r'\{[\s\S]*?\}', cached_suggestions)
                    if json_matches:
                        for match in json_matches:
                            json.loads(match)
                        is_cache_valid = True
                except (json.JSONDecodeError, AttributeError, TypeError):
                    is_cache_valid = False
                if is_cache_valid:
                    self.kernel.write_to_log(f"AI Co-pilot: CACHE HIT for preset '{preset_name}' (AI: {os.path.basename(str(active_master_ai_id))}).", "INFO")
                    self._process_and_publish_ai_suggestions(cached_suggestions, context_id)
                    return
                else:
                    self.kernel.write_to_log(f"AI Co-pilot: Corrupt cache detected for '{preset_name}'. Deleting and re-analyzing.", "WARN")
                    self.state_manager.delete(cache_key)
            self.kernel.write_to_log(f"AI Co-pilot: CACHE MISS for preset '{preset_name}' (AI: {os.path.basename(str(active_master_ai_id))}). Analyzing...", "WARN")
            metrics_for_context = self._get_metrics_for_context(context_id)
            history_summary = self._summarize_metrics(metrics_for_context)
            if history_summary:
                if not active_master_ai_id:
                    raise ConnectionError("No default AI for Text is configured in Settings for Co-pilot analysis.")
                analysis_prompt = self._create_analysis_prompt(history_summary)
                ai_manager = self.kernel.get_service("ai_provider_manager_service")
                self.kernel.write_to_log(f"AI Co-pilot: Sending prompt to default Text AI for analysis.", "INFO")
                ai_response = ai_manager.query_ai_by_task('text', analysis_prompt)
                if "error" in ai_response:
                    raise ConnectionError(f"AI Co-pilot analysis failed: {ai_response['error']}")
                raw_suggestions = ai_response.get("data", "[]")
                self.state_manager.set(cache_key, raw_suggestions)
                self.kernel.write_to_log(f"AI Co-pilot: New suggestions for '{preset_name}' saved to cache.", "INFO")
                self._process_and_publish_ai_suggestions(raw_suggestions, context_id)
        except subprocess.TimeoutExpired:
            error_msg = f"AI Worker process for model '{os.path.basename(str(active_master_ai_id))}' timed out. The model may be too large for your hardware, or you can increase the timeout in settings."
            self.kernel.write_to_log(error_msg, "CRITICAL")
        except Exception as e:
            self.kernel.write_to_log(f"AI Co-pilot analysis thread encountered an error: {e}", "ERROR")
            traceback.print_exc()
        finally:
            if self.event_bus:
                self.event_bus.publish("AI_ANALYSIS_FINISHED", {})
    def invalidate_suggestion_cache(self, preset_name: str):
        if not self.preset_manager or not self.state_manager: return
        try:
            preset_data = self.preset_manager.get_preset_data(preset_name)
            if not preset_data: return
            active_master_ai_id = self.loc.get_setting("ai_model_for_text", "default_ai")
            logical_structure = {
                'nodes': [{k: v for k, v in node.items() if k not in ['x', 'y']} for node in preset_data.get('nodes', [])],
                'connections': preset_data.get('connections', [])
            }
            workflow_str = json.dumps(logical_structure, sort_keys=True) + str(active_master_ai_id)
            workflow_hash = hashlib.md5(workflow_str.encode('utf-8')).hexdigest()
            cache_key = f"ai_suggestion::{preset_name}::{workflow_hash}"
            self.state_manager.delete(cache_key)
            self.kernel.write_to_log(f"AI suggestion cache invalidated for preset '{preset_name}'.", "INFO")
        except Exception as e:
            self.kernel.write_to_log(f"Failed to invalidate suggestion cache for '{preset_name}': {e}", "WARN")
    def _suggestion_publisher(self, message, level, context=None):
        if level in ["WARN", "ERROR", "CRITICAL", "MINOR"]:
            if context is None: context = {}
            suggestion_text = re.sub(r'\s*\[\w+\]\s*->\s*', '', message)
            event_payload = {
                "preset_name": context.get("preset_name", "N/A"),
                "node_id": context.get("node_id", "N/A"),
                "node_name": context.get("node_name", "N/A"),
                "suggestion_text": suggestion_text,
                "severity": level
            }
            if event_payload["node_id"] != "N/A":
                if self.event_bus:
                    self.event_bus.publish("OPTIMIZATION_SUGGESTION_FOUND", event_payload)
    def _get_metrics_for_context(self, target_context_id: str) -> list:
        try:
            history_file_path = os.path.join(self.kernel.data_path, "metrics_history.jsonl")
            with open(history_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            relevant_metrics = []
            for line in lines:
                try:
                    log_entry = json.loads(line)
                    metric = log_entry.get("metrics", {})
                    if metric.get('workflow_context_id') == target_context_id:
                        relevant_metrics.append(metric)
                except json.JSONDecodeError:
                    continue
            return relevant_metrics
        except FileNotFoundError:
            return []
    def _summarize_metrics(self, metrics: list) -> str:
        if not metrics:
            return "The workflow execution completed successfully with no metrics recorded. Please confirm this is expected."
        MAX_METRICS_TO_SUMMARIZE = 50
        if len(metrics) > MAX_METRICS_TO_SUMMARIZE:
            self.kernel.write_to_log(f"Metrics history is too long ({len(metrics)} entries). Truncating to the last {MAX_METRICS_TO_SUMMARIZE} for AI analysis.", "WARN")
            metrics = metrics[-MAX_METRICS_TO_SUMMARIZE:]
        execution_sequence = " -> ".join([f"{m.get('node_name', '?')} (ID: {m.get('node_id')})" for m in metrics])
        error_nodes = [
            f"- Node '{m.get('node_name')}' (ID: {m.get('node_id')}) FAILED."
            for m in metrics if m.get('status') == 'ERROR'
        ]
        slow_nodes = [
            f"- Node '{m.get('node_name')}' (ID: {m.get('node_id')}) was slow, taking {m.get('execution_time_ms', 0):.0f} ms."
            for m in metrics if m.get('execution_time_ms', 0) > 2000
        ]
        summary_parts = [f"Execution Sequence: {execution_sequence}"]
        if error_nodes:
            summary_parts.append("\nErrors Detected:")
            summary_parts.extend(error_nodes)
        if slow_nodes:
            summary_parts.append("\nPerformance Issues:")
            summary_parts.extend(slow_nodes)
        if not error_nodes and not slow_nodes:
            summary_parts.append("\nAnalysis: All nodes executed successfully without any obvious errors or performance delays.")
        total_nodes = len(metrics)
        summary_parts.append(f"\nSummary: {total_nodes} nodes executed. {len(error_nodes)} failed, {len(slow_nodes)} were slow.")
        return "\n".join(summary_parts)
    def _create_analysis_prompt(self, summary_text: str) -> str:
        return self.loc.get(
            'ai_copilot_prompt',
            fallback="Please analyze the following text: {summary_text}",
            summary_text=summary_text
        )
    def _process_and_publish_ai_suggestions(self, raw_data, context_id):
        if not self.state_manager: return
        open_tabs = self.state_manager.get("open_tabs", [])
        open_tab_ids = {tab.get('tab_id') for tab in open_tabs}
        if context_id not in open_tab_ids:
            return
        suggestions = []
        try:
            json_matches = re.findall(r'\{[\s\S]*?\}', raw_data)
            if not json_matches:
                self.kernel.write_to_log(f"AI Co-pilot could not find any valid JSON object in the response: {raw_data}", "WARN")
                return
            for match_str in json_matches:
                try:
                    suggestion_obj = json.loads(match_str)
                    suggestions.append(suggestion_obj)
                except json.JSONDecodeError:
                    self.kernel.write_to_log(f"AI Co-pilot found a malformed JSON object, skipping: {match_str}", "DEBUG")
                    continue
            if not suggestions:
                self.kernel.write_to_log(f"AI Co-pilot found JSON-like blocks but failed to parse any of them as valid suggestions.", "WARN")
                return
            self.kernel.write_to_log(f"AI Co-pilot successfully parsed {len(suggestions)} new suggestions from the master AI.", "SUCCESS")
            for suggestion in suggestions:
                if all(k in suggestion for k in ['node_name', 'node_id', 'suggestion']):
                    preset_name_from_state = self.state_manager.get(f"tab_preset_map::{context_id}", "N/A")
                    context = {
                        "preset_name": preset_name_from_state,
                        "node_id": suggestion.get('node_id'),
                        "node_name": suggestion['node_name']
                    }
                    self._suggestion_publisher(suggestion['suggestion'], "WARN", context)
                else:
                    self.kernel.write_to_log(f"AI Co-pilot skipped a suggestion object due to missing keys: {suggestion}", "WARN")
        except Exception as e:
             self.kernel.write_to_log(f"A critical error occurred in _process_and_publish_ai_suggestions: {e}", "ERROR")
