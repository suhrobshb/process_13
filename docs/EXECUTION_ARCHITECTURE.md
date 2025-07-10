# AI Engine: Execution Architecture Guide

This document explains how the AI Engine executes your automated workflows, detailing the different execution environments and answering the critical question: **"Does my computer need to be on?"**

The AI Engine is designed with a flexible, hybrid architecture to handle any automation scenario. There are two primary execution models:

1.  **Cloud-Based Execution**: For web, API, and cloud application tasks. **Your laptop can be turned off.**
2.  **Local Agent Execution**: For tasks involving desktop applications installed on your computer. **Your laptop must be on.**

---

## 🌐 Model 1: Cloud-Based Execution (Default & Recommended)

This is the primary execution model for the AI Engine. Your workflows run on secure, scalable cloud servers, which we call **"Cloud Workers"** or **"Digital Employees"**.

### How It Works

When you trigger a workflow that involves web browsing, API calls, or interacting with cloud software (like Office 365, Salesforce, etc.), the AI Engine executes it entirely within our cloud infrastructure.

```mermaid
graph TD
    subgraph Your Environment
        A[👩‍💼 User's Browser]
    end

    subgraph AI Engine Cloud Platform
        B[Dashboard UI & API]
        C[Workflow Orchestrator]
        D[🤖 Cloud Worker Fleet]
        E[Headless Browsers & API Clients]
    end
    
    subgraph Target Applications
        F[Public Websites / Web Apps]
        G[Third-Party APIs]
        H[Cloud Software (e.g., O365)]
    end

    A -- "Start Workflow 'Process Invoices'" --> B
    B -- "Trigger Workflow #123" --> C
    C -- "Assigns Job" --> D
    D -- "Executes Steps" --> E
    E -- "Interacts with..." --> F
    E -- "Calls..." --> G
    E -- "Connects to..." --> H
```

### Key Characteristics

-   **Laptop Status**: **OFF**. Your computer is only needed to create, manage, and monitor the workflows via the web dashboard. The execution itself is 100% cloud-based and runs 24/7, regardless of your local machine's status.
-   **Scalability**: We can run thousands of workflows in parallel by scaling the number of Cloud Workers.
-   **Security**: All operations run in an isolated, secure cloud environment. Your local machine is never directly exposed.
-   **Best For**:
    -   Automating tasks in web-based applications (CRMs, ERPs, etc.).
    -   Integrating with third-party APIs.
    -   Processing data from cloud sources.
    -   Running scheduled tasks at any time, day or night.

---

## 🖥️ Model 2: Local Agent Execution (For Desktop Apps)

For workflows that need to interact with software installed *only on your computer* (like a legacy accounting application or a specific version of Excel), the AI Engine uses a secure **Local Agent**.

### How It Works

The Local Agent is a small, secure application you install on your computer. When a workflow needs to perform a desktop action, the cloud orchestrator sends a secure command to the Local Agent, which then executes the mouse and keyboard actions on your machine.

```mermaid
graph TD
    subgraph AI Engine Cloud Platform
        A[Workflow Orchestrator]
    end

    subgraph Your Local Environment
        B[User's Laptop (Must be ON)]
        C[🔒 AI Engine Local Agent]
        D[🖱️ Keyboard & Mouse Control]
        E[🏢 Desktop Application (e.g., QuickBooks Desktop)]
    end

    A -- "Securely sends command: 'Click Save Button'" --> C
    C -- "Executes on your machine" --> D
    D -- "Performs click" --> E
```

### Key Characteristics

-   **Laptop Status**: **ON**. Your computer must be turned on, logged in, and the Local Agent application must be running for these specific workflows to execute.
-   **Security**: The agent establishes a secure, outbound-only connection to the cloud. No inbound ports need to be opened on your firewall. All actions are logged and auditable.
-   **Best For**:
    -   Automating legacy desktop software that has no API.
    -   Interacting with applications inside a private corporate network.
    -   Workflows that require access to local files on your machine.

---

## ⚖️ How the AI Engine Decides Which Model to Use

The choice is made automatically based on the **Action Step Boxes** in your workflow.

-   If a workflow **only** contains `HTTP Request`, `Browser Action`, and `LLM Prompt` steps, it will run **entirely in the cloud**.
-   If a workflow contains even **one** `Shell Command` or `Desktop Action` step, that specific step (and any subsequent steps that depend on it) must be executed by a **Local Agent**.

You can build **hybrid workflows** that perform some steps in the cloud and others on a local machine, giving you maximum flexibility.

### Comparison Table

| Feature | Cloud-Based Execution | Local Agent Execution |
| :--- | :--- | :--- |
| **Laptop Requirement** | **OFF** | **ON** |
| **Primary Use Case** | Web Apps, APIs, Cloud Software | Desktop Apps, Local Files |
| **Scalability** | High (Thousands of parallel runs) | Limited to the local machine's capacity |
| **Availability** | 24/7, 365 days a year | Only when the user's machine is active |
| **Security** | Isolated cloud environment | Runs on user's machine with their permissions |
| **Example Action** | "Fill form on `salesforce.com`" | "Click 'Save' in QuickBooks Desktop" |

---

## ✅ Conclusion: The Best of Both Worlds

This hybrid architecture ensures the AI Engine is both **powerful and universally compatible**.

-   For **90% of modern business tasks** involving web and cloud applications, you can set your workflows to run 24/7 and completely forget about them, knowing they are executing reliably in the cloud.
-   For that **10% of critical tasks** tied to specific desktop software, the Local Agent provides a secure bridge, ensuring no process is left behind.

This flexibility allows the AI Engine to be a single, unified platform for automating **every aspect** of your business operations.

