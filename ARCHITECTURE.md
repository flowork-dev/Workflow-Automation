# Flowork System Architecture

Flowork is engineered as a revolutionary **Split-Brain Distributed System** designed for **massive scalability** and **absolute user data sovereignty**. Our architecture guarantees that the core processing and sensitive data remain exclusively on the user's self-hosted server.

## 1. The Core Philosophy: Decentralized Trust (Local Engine)

Our design is based on the principle: **The GUI is a window; the Engine is the vault.**

| Component | Location | Role |
| :--- | :--- | :--- |
| **User Interface (GUI)** | Cloudflare Pages (Global CDN) | State-less presentation layer. Handles UI/UX and non-sensitive API communication. |
| **Gateway (API)** | User's Local Server (Docker) | **Authentication & Routing.** Validates Web3 crypto-signatures, manages engine sessions, and securely proxies requests to the Core Engine. |
| **Core Engine** | User's Local Server (Docker) | **The Execution Kernel.** Executes workflows, accesses local AI models, manages local database (SQLite), and handles all user data. |
| **Cloudflare Tunnel** | User's Local Server (Docker) | Creates a secure, outbound connection from the user's server to the global GUI, bypassing NAT and firewalls for seamless access. |

## 2. Execution & Performance Model

The internal design of the Gateway/Core cluster prioritizes **Zero-Latency Execution** while maintaining a clean API boundary:

1.  **API Decoupling:** The Gateway communicates with the Core Engine (on port 8989) exclusively via HTTP/API, treating it as a separate service despite running locally in Docker. This simplifies maintenance and debugging.
2.  **In-Process Kernel (Legacy/Debug):** While the production model is containerized, the internal kernel structure supports low-latency *in-process* execution for specific modules or debugging, achieving maximum performance when decoupling overhead is undesirable. This duality is managed at the code level but enforced as separate containers in production.
3.  **Local AI Powerhouse:** The Core Engine is responsible for running local AI models (e.g., Llama-cpp-python, SDXL), ensuring that heavy computation and proprietary data processing never leave the user's hardware.

## 3. Security & Access Layer (Web3 Crypto)

Access control is built upon Web3 principles for robustness:

* **Crypto-Secured Access:** Authentication relies on **Admin Login Private Key** signatures (e.g., ECDSA), which are verified by the Gateway. This eliminates traditional password vulnerabilities and ensures that the user's identity is cryptographically proven before API requests are routed.
* **Data Isolation:** All session data, user configurations, and workflow history are stored in the local SQLite database, ensuring **All databases reside exclusively on your server**.

## 4. Scaling the Network (Collaboration Model)

To support **"One Engine can be utilized by multiple Users"**, the Gateway manages a secure permission layer (`flowork-gateway/app/routes/shares.py`, etc.) that controls external user access to the local Core Engine's resources, all while operating through the trusted Cloudflare Tunnel connection.