# Flowork Project Roadmap

This document outlines the strategic direction and planned feature milestones for Flowork. Note that this roadmap is subject to change based on community feedback, technical feasibility, and emerging AI trends.

## Phase 1: V1.0 - Hardening and Community Foundation (Current Focus - Q4 2025) (English Hardcode)

| Focus Area | Key Deliverables | Rationale |
| :--- | :--- | :--- |
| **Security & Stability** | Finalize `SECURITY.md`, complete external security audit, fix all critical bugs related to the Engine Sharing permission layer. | Essential for a crypto-secured, self-hosted platform to build trust. |
| **Core Architecture** | Fully deprecated all remaining *in-process* Core logic references; enforce strict API boundaries between Gateway and Core Engine. | Ensure clean architectural separation for long-term maintenance and scaling. |
| **Community Tools** | Stable release of `CONTRIBUTING.md`, `GOVERNANCE.md`, and this `ROADMAP.md`. Introduce a formal CI/CD pipeline for community contributions. | Professionalize the development workflow to attract quality contributions. |

## Phase 2: V1.1 - Decentralized Features & UX Polishing (H1 2026) (English Hardcode)

| Focus Area | Key Deliverables | Rationale |
| :--- | :--- | :--- |
| **Engine Interoperability** | **Secure Cross-Engine API Calls:** Allow a Workflow on Engine A to securely trigger a Workflow on Engine B (owned by a different user) using signed requests. | Fully enable the "many engines, many users" vision for network collaboration. |
| **Advanced Local AI** | Native support for popular local LLM platforms (e.g., Ollama, MLX) through new AI Providers. | Deepen commitment to Local AI and user resource utilization. |
| **WebSockets** | Implement scalable, resilient WebSocket session management for real-time *Time Traveler Debugger* updates, supporting high latency over Cloudflare Tunnels. | Improve developer experience in the self-hosted environment. |

## Phase 3: V2.0 - Global Mesh Network & Autonomy (Long Term) (English Hardcode)

* **Decentralized Service Discovery:** Implement a *Gossip Protocol* or a similar decentralized ledger to allow users to securely "discover" public or shared Engines without a centralized registry.
* **Edge Processing Optimization:** Integrate WebAssembly (WASM) runners into the Gateway/Core to allow execution of simple modules at the very edge (potentially Cloudflare Workers or similar) for ultra-low latency tasks.
* **Fully Autonomous Agents:** Enhanced Core Kernel capabilities to run complex, multi-tool AI Agents that persist context across multiple workflow executions.

---