# Flowork Changelog

All notable changes to the Flowork project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning (SemVer).

## [1.0.0] - 2025-10-30 (English Hardcode - Example Version)

### 🚀 Major Architectural Changes (English Hardcode)
* **Decoupling:** Full transition of the Core Kernel from an in-process execution model to a dedicated, API-accessed Docker container. This ensures true scalability and resource isolation for self-hosted users.
* **Database:** Default database for the Gateway reverted to **SQLite** for zero-setup local deployment, with clear documentation for PostgreSQL/MySQL scalability.
* **Network:** Health-check and Core discovery logic modified to exclusively target the local Core Engine via hardcoded `http://flowork-core:8989`, eliminating irrelevant distributed load-balancing logic.

### ✨ Added (English Hardcode)
* Implemented initial framework for Engine Sharing and multi-user access (one Engine, many Users).
* Added `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, and `LICENSE.md` to establish community guidelines.
* New system diagnostics plugin (`plugins/system_diagnostics_plugin`).

### 🛠️ Fixed (English Hardcode)
* Fixed a critical logic bug in `get_next_core_server` that incorrectly used random selection in a single-engine deployment model.
* Removed deprecated in-process user data injection function `_inject_user_data_to_core` from `core_utils.py` to enforce clean API boundaries.

### 🗑️ Removed (English Hardcode)
* Removed explicit volume mounts for user Desktop, Documents, etc., from `docker-compose.yml` for improved security and portability (relying only on necessary shared volumes).