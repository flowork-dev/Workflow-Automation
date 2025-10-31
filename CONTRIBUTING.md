# Contributing to Flowork

We are thrilled that you are interested in contributing to Flowork, the self-hosted AI workflow automation platform focused on user data sovereignty. As an open-core project, we rely on the community for both growth and innovation.

**Important Note:** The Core Logic and Engine run on the user's local server to preserve privacy and data sovereignty. Therefore, contributions that focus on **robust local execution** and **security enhancements** are highly valued.

## How to Contribute?

There are many ways you can help, not just by writing code.

### 🐛 1. Reporting Bugs

If you find a bug or an unexpected failure, please report it via our GitHub Issues page.

**Bug Reporting Guidelines:**
1.  **Check First:** Search existing Issues to ensure the bug hasn't already been reported.
2.  **Provide Detail:** Clearly describe the steps necessary to reproduce the bug (**minimal replication steps**).
3.  **Environment Details:** Include essential information such as your Flowork version, the host operating system running Docker, and any relevant configurations (e.g., modified parts of your `docker-compose.yml`).
4.  **Include Logs:** Attach relevant log snippets from the `flowork_gateway` or `flowork_core` containers.

### ✨ 2. Suggesting Features

We welcome revolutionary new ideas! Please use the **Issues** page to propose new features.

**Feature Suggestion Guidelines:**
1.  **Describe the Problem:** Explain the problem you are trying to solve and why this feature is critical for Flowork's self-hosted architecture.
2.  **Usage Scenario:** Provide specific examples of how the new feature would be used by the end-user.
3.  **Avoid Duplication:** Verify that a similar feature proposal does not already exist.

### 💻 3. Code Contributions (Pull Requests)

We accept Pull Requests (PRs) for bug fixes, feature enhancements, and new Modules/Plugins.

1.  **Fork and Clone:** Fork the Flowork repository to your GitHub account and clone it locally.
2.  **Create a New Branch:** Always work on a new, descriptively named branch (e.g., `fix/name-of-bug` or `feat/new-feature-name`).
3.  **Code Style Compliance:** Ensure your code adheres to the *linting* and *formatting* standards used in the project (we use Python, please ensure PEP 8 style).
4.  **Unit Tests:** Include or update relevant unit tests for your code changes.
5.  **Update Documentation:** If your change affects how a Module, Plugin, or Tool works, update the relevant documentation (including the `locales/en.json` file if user-facing text is changed).
6.  **Submit PR:** Submit your Pull Request to the `main` branch of the Flowork repository. Ensure your PR references the related Issue.

## 🤝 Architectural Consultation

If you plan to implement major architectural changes (e.g., modifying how the proxy works or inter-Engine communication), please open a **Discussion** first. We want to ensure Flowork remains agile, secure, and compatible with its massive self-hosted scalability goal.