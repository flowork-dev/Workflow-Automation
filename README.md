# ✨ Visual AI Workflow Automation Platform
<p align="center">
  <img src="https://flowork.cloud/images/flowork_2.webp" alt="Flowork Synapse Logo"/>
</p>


[](https://github.com/flowork-dev/Visual-AI-Workflow-Automation-Platform)
[](https://docs.flowork.cloud/)
[](https://t.me/FLOWORK_AUTOMATION)
[](https://discord.gg/Gv7h5fWZY)
[](https://www.youtube.com/playlist?list=PLATUnnrT5igDXCqjBVvkmE4UKq9XASUtT)

Flowork is an open-core, self-hosted AI workflow orchestration engine **designed for *Global Distributed Scalability and Full User Data Sovereignty***. Flowork's architecture enables **millions of self-hosted deployments** worldwide, ensuring full control over your data and resources. Flowork separates the interface (GUI in the *cloud*) from the core logic (Gateway and Core on your server), giving you full control over your data and resources.

## 🌟 Table of Contents

1.  [✨ Core Philosophy: Privacy & Data Sovereignty](#core-philosophy-privacy--data-sovereignty)
2.  [🚀 Architectural Advantages & Performance](#architectural-advantages--performance)
3.  [🌐 Multi-Language Runner Engine](#multi-language-runner-engine)
4.  [🔌 OS-Native Triggering and Automation](#os-native-triggering-and-automation)
5.  [🧠 AI Powerhouse & Developer Tools](#ai-powerhouse--developer-tools)
6.  [🔗 Collaboration & Resource Sharing](#collaboration--resource-sharing)
7.  [🛠️ Debugging and Diagnostics Features](#debugging-and-diagnostics-features)
8.  [⚙️ Quick Installation & Setup Guide (Docker)](#quick-installation--setup-guide-docker)
9.  [🌐 Resources & Community](#resources--community)

-----

## 1. ✨ Core Philosophy: Privacy & Data Sovereignty

We ensure user privacy with the principle: **"Your Data on Your Server."**

  * **User Data Sovereignty (Primary Privacy):** **All databases** (SQLite/PostgreSQL) and private user data **reside exclusively on your server** (self-hosted). Flowork never stores your sensitive data on third-party servers.
  * **Crypto-Secured Access (Zero-Trust):** We utilize **Web3 Crypto Technology (Private Key)** for admin and user authentication. This ensures that access to your Engine is cryptographically verified, providing a robust, anti-phishing, **zero-trust** security layer.
  * **Enterprise Ready Audit Trail:** All administrative activities are logged in a local **Audit Log** on the user's server, essential for data compliance and security requirements.

## 2. 🚀 Architectural Advantages & Performance

Flowork's architecture is designed from the ground up to handle massive, distributed execution loads simultaneously with minimal latency.

  * **Decoupled Execution Model:** Our Core Kernel is run in a separate container/process from the Gateway, ensuring clean separation and the highest stability for distributed deployment.
  * **AI Provider Agnostic:** Not locked into a single AI provider. Users are free to choose between cloud AI (Gemini, ChatGPT) or **Local AI** (*on-premise*) models running on their hardware.
  * **Resource Efficiency:** Uses **SQLite** as the default *file-based* database for **zero-setup** and resource efficiency (*RAM/CPU*), while being ready for scaling with PostgreSQL/Redis.

## 3. 🌐 Multi-Language Runner Engine

Flowork's Core Compiler is built to execute logic across multiple native scripting environments, ensuring seamless integration with existing tools and codebases.

  * **Polyglot Workflow Execution:** Execute code modules written in **Python, JavaScript, Bash, PHP, Perl, and Ruby** directly within your visual workflow.
  * **Seamless Integration:** Eliminates the need for external wrapper services when integrating legacy scripts or domain-specific languages.

## 4. 🔌 OS-Native Triggering and Automation

Leverage the power of your local machine to automatically initiate workflows based on system-level events, perfect for data-sensitive automation tasks.

  * **File System Watchers:** Trigger workflows instantly upon changes (creation, modification, deletion) in specified local directories or files.
  * **Process & Cron Monitoring:** Initiate tasks based on sophisticated Cron schedules or the status of other running local processes.

## 5. 🧠 AI Powerhouse & Developer Tools

Flowork is a platform that empowers developers and integrates AI deeply and flexibly.

  * **Integrated AI Training:** Supports workflows for **AI Model Training** conducted entirely within your server environment.
  * **Local AI Support:** Our modular architecture supports *on-premise* AI models running on your hardware (e.g., models powered by **llama-cpp-python** or Stable Diffusion XL).
  * **AI Analyzer:** An intelligent feature to analyze your workflows, identify potential *bottlenecks*, and provide automated optimization suggestions.
  * **Component Factory Tools:** We provide comprehensive tools to help developers rapidly create custom **Modules, Triggers, Plugins, and Tools**.

## 6. 🔗 Collaboration & Resource Sharing

  * **Engine Sharing:** Users can **share access to their Engine** (server) with other Flowork users under strict permission control. **One *Engine* can be utilized by multiple *Users***, optimizing your hardware investment.
  * **Preset Sharing:** Easily share your created *workflows* or *presets* with your team or the community.

## 7. 🛠️ Debugging and Diagnostics Features

  * **System Integrity Engine:** Automatically verifies the integrity of core files and add-ons before execution, ensuring the self-hosted instance is tamper-proof.
  * **Time Traveler Debugger:** We offer comprehensive *debugging* that lets you inspect the data *state* (*variables* and *payload*) **after every node** is executed, essential for tracking complex workflow errors.
  * **Quick Run Mode:** Allows developers to execute **a single *module* independently** (like a *function* call in an IDE) for quick testing and debugging.

## 8. ⚙️ Quick Installation & Setup Guide (Docker)

This guide assumes you are using Docker Compose for local setup.

### Prerequisites (English Hardcode)

  * Docker Desktop (or Docker Engine)
  * Python 3.11+ (for running the setup script)

### Installation Steps (English Hardcode)

1.  **Generate Environment:** Create new Engine ID, Token, and the **Admin Login Private Key** for a clean setup.

    ```bash
    python generate_env.py
    ```

2.  **Build and Run Containers:** Build and *re-create* the **Gateway** container (which encapsulates the Core Kernel, database migration, and all AI/ML dependencies).

    ```bash
    # IMPORTANT: Use --force-recreate --no-cache for the first run or after major code changes.
    docker-compose up --build --force-recreate -d
    # For subsequent restarts:
    docker-compose up -d
    ```

3.  **Get Private Key (Login):** Check the Gateway logs to retrieve the newly generated admin *private key*.

    ```bash
    docker-compose logs flowork_gateway
    # Search for: !!! YOUR LOGIN PRIVATE KEY IS: ...
    ```

### Cloudflare Tunnel Configuration (Required for Global/GUI Access)

The Flowork GUI (hosted on Cloudflare Pages) accesses your API via a tunnel.

1.  **Get Token:** Obtain your **Cloudflare Tunnel Token** from your Cloudflare dashboard.
2.  **Set in .env:** Ensure the `CLOUDFLARED_TUNNEL_TOKEN` in your `.env` file is set.
3.  **Restart Container:** Restart the `flowork_cloudflared` container (or the entire *stack*) for the tunnel to connect to the Gateway service (`http://flowork_gateway:8000`).

## 9. 🌐 Resources & Community

Join our community! We are rapidly growing and welcome your contributions and feedback.

| Platform | Link |
| :--- | :--- |
| **website** | [https://flowork.cloud](https://flowork.cloud) |
| **GitHub Repo** | [https://github.com/flowork-dev/Visual-AI-Workflow-Automation-Platform.git](https://github.com/flowork-dev/Visual-AI-Workflow-Automation-Platform) |
| **Documentation (Docs)** | [https://docs.flowork.cloud/](https://docs.flowork.cloud/) |
| **Telegram Channel** | [https://t.me/FLOWORK\_AUTOMATION](https://t.me/FLOWORK_AUTOMATION) |
| **YouTube Playlist** | [https://www.youtube.com/playlist?list=PLATUnnrT5igDXCqjBVvkmE4UKq9XASUtT](https://www.youtube.com/playlist?list=PLATUnnrT5igDXCqjBVvkmE4UKq9XASUtT) |
| **Discord Server** | [https://discord.gg/Gv7h5d5d](https://discord.gg/Gv7h5d5d) |