
# AI Engine - RAG, LangChain & Intelligent Automation Guide

This guide explains the powerful **Retrieval-Augmented Generation (RAG)** capabilities integrated into the AI Engine. This is the intelligence layer that allows your workflows to understand your private documents, participate in email conversations, and make context-aware decisions, transforming the engine from a simple task executor into a cognitive automation platform.

---

## 1. The Challenge: Generic LLMs Don't Know Your Business

Standard Large Language Models (LLMs) like GPT-4 are incredibly powerful but have a fundamental limitation: **they have no knowledge of your internal, private, or real-time business data.** This prevents them from answering specific questions or making nuanced decisions relevant to your operations.

**The Solution: Retrieval-Augmented Generation (RAG)**

RAG bridges this knowledge gap. It empowers the AI Engine to:
1.  **Retrieve** relevant information from your private data sources (PDFs, documents, emails, web pages).
2.  **Augment** the LLM's prompt with this retrieved, factual context.
3.  **Generate** an intelligent, accurate response or decision based on *your* data, not just its general knowledge.

We use the **LangChain** framework to robustly handle the data processing, vectorization, and query orchestration required for this process.

---

## 2. Architecture: How RAG Powers the AI Engine

The RAG system is seamlessly integrated into the workflow engine, acting as a "just-in-time" knowledge provider for your automated processes.

```mermaid
graph TD
    subgraph User's Private Data Space
        A[📄 PDFs, Docs, Emails]
    end

    subgraph AI Engine's Secure Tenant Space
        B(1. Data Ingestion API)
        C(2. RAGEngine w/ LangChain)
        D[3. Vector Store (FAISS) per User]
    end
    
    subgraph Workflow Execution
        E[Workflow Step]
        F(4. LLM Runner)
        G[🤖 OpenAI API]
        H[✅ Final Output]
    end

    A -- Upload/Connect --> B
    B -- Triggers Processing --> C
    C -- Loads, Splits & Embeds --> D
    E -- "Needs context for a task" --> F
    F -- "What is the policy for X?" --> D
    D -- "Here are relevant snippets" --> F
    F -- "Context: [Snippets]. Question: [Original Query]" --> G
    G -- "Based on the context, the answer is..." --> F
    F -- Returns Intelligent Result --> H
```

**The Flow Explained:**
1.  **Data Ingestion**: You provide the AI Engine with access to your documents (e.g., upload PDFs of company policies, connect to an email inbox).
2.  **Processing (LangChain)**: The `RAGEngine` uses LangChain to load the documents, split them into manageable chunks, and convert them into numerical representations (embeddings) using an AI model.
3.  **Vector Store**: These embeddings are stored in a secure, tenant-isolated vector database (like FAISS), which acts as a searchable long-term memory for the AI.
4.  **Intelligent Execution**: When a workflow step needs information, it queries the vector store. The most relevant document snippets are retrieved and injected into the prompt sent to the main LLM (e.g., GPT-4), ensuring the AI's response is grounded in your specific data.

---

## 3. The Anatomy of an Intelligent Action Step Box

With RAG, our action step boxes become much more sophisticated. They follow a clear `Input -> Process -> Output` structure.

 <!-- Placeholder for a visual diagram -->

### **Inputs**
-   **If it's the first box in a workflow:** The input can come from an external source like a new email, a newly uploaded document, or a webhook trigger.
-   **If it's a subsequent box:** The input is typically the output from one or more preceding boxes. It can also pull in new external data if needed.

### **Process**
-   **LLM Intention Analysis**: The core of the box. The LLM understands the *business goal* of this step (e.g., "Assess financial risk," "Draft a follow-up email").
-   **Context Retrieval (RAG)**: If the process requires specific knowledge, it queries the vector store to retrieve relevant context. For example, to "Assess financial risk," it would retrieve data from an uploaded financial report.
-   **Execution**: The LLM, now equipped with context, executes the process. This could involve generating text, making a decision, or preparing data for the next step.
-   **Scenario Handling**: A single process can have multiple potential outcomes. For example, a "Negotiate Rate" process could result in "Rate Accepted," "Rate Rejected," or "Counter-offer Needed." The AI can determine the outcome and route the workflow accordingly.

### **Outputs**
-   The direct result of the process. This could be a generated email draft, a summary of a document, a "true/false" decision, or a structured JSON object.
-   These outputs are then passed as inputs to the next connected action step box(es), creating a seamless data flow through the entire workflow.

---

## 4. Practical Application: The Logistics Dispatch Scenario

Let's see how this applies to the logistics workflow we discussed.

1.  **Input**: An email arrives in Outlook from a broker with a PDF rate confirmation attached.
2.  **Action Box 1: "Analyze Incoming Load Request"**
    *   **Input**: The new email and its PDF attachment.
    *   **Process (RAG)**:
        1.  The AI Engine is triggered by the new email.
        2.  It uses LangChain's `PyPDFLoader` to read the rate confirmation PDF.
        3.  It queries its knowledge base (vector store) of past loads to check historical rates for this lane.
        4.  The LLM analyzes the email content and the PDF data, comparing the offered rate to historical averages.
    *   **Output**: A structured JSON object: `{ "is_rate_good": true, "broker": "CH Robinson", "lane": "LAX-DFW", "details": {...} }`.
3.  **Action Box 2: "Decision: Accept or Negotiate?"**
    *   **Input**: The JSON output from the previous step.
    *   **Process**: A simple decision node checks the `is_rate_good` field.
    *   **Output**: Routes the workflow to either the "Accept" path or the "Negotiate" path.
4.  **Action Box 3: "Draft Negotiation Email"** (if rate is not good)
    *   **Input**: The details from Action Box 1.
    *   **Process (RAG + LLM)**:
        1.  The LLM is prompted: "Draft a polite but firm negotiation email to [Broker]. Our target rate for the [Lane] lane is [Historical Rate]. The offered rate is [Offered Rate]."
        2.  The LLM generates a professional email draft.
    *   **Output**: The text of the email, ready to be sent.

---

## 5. Advanced Workflow Structures

This intelligent, context-aware approach unlocks more complex and powerful workflow designs.

### **Decision Trees**
Instead of simple if/else logic, you can create complex decision trees. The `RAGDecisionRunner` can evaluate a situation against your knowledge base and choose from multiple possible outcomes, each leading to a different branch of the workflow.

### **Parallel Processing**
Since some steps might be independent, the engine can execute them in parallel. For example, while one step is waiting for a human approval, another can proceed with data analysis from a different document source.

---

## 6. Pre-built Workflow Templates

To accelerate setup, the AI Engine can provide pre-built templates for common business processes. These are not just static workflows but are designed to be "trained" with your data.

**Examples:**
-   **Employee Onboarding**: A template that you "teach" by providing your company's specific onboarding documents and policies.
-   **Invoice Processing**: A template that learns the format of your vendors' invoices to automate data extraction.
-   **Customer Support Triage**: A template that learns from your past support tickets how to categorize and route new inquiries.

---

## 7. Monthly Cost Estimation

The cost of running the AI Engine depends on usage, but here's a typical breakdown for a moderately active small team:

| Service | Component | Estimated Monthly Cost | Notes |
| :--- | :--- | :--- | :--- |
| **AI & LLM** | OpenAI API | **$20 - $100+** | Based on number of workflow executions. A complex RAG query might cost $0.01 - $0.05. |
| | Embeddings | **$1 - $5** | One-time cost per document ingestion, very cheap. |
| **Cloud Hosting** | GCP Cloud Run | **$5 - $20** | For hosting the API and workers. Scales with traffic. |
| | Cloud SQL (Postgres) | **$15 - $30** | For the primary database. |
| | Vector Database | **$0 (local)** | We use FAISS, which runs on the same server. Cloud options like Pinecone exist for larger scale. |
| | Cloud Storage | **$1 - $5** | For storing uploaded documents and vector indexes. |
| **Total Estimated** | | **$42 - $160+ / month** | **Highly dependent on the number and complexity of workflows.** |

**Key Takeaway**: The primary operational cost is the LLM API usage, which is directly tied to how many intelligent tasks your workflows perform.

---

## 8. Security & Data Privacy

This powerful integration is designed with security as a top priority:
-   **Tenant Isolation**: Your data, including documents and vector stores, is strictly isolated to your user account and tenant. No other user can access it.
-   **Controlled Access**: The LLM does not get free-roaming access to your data. The RAG engine only retrieves and provides the most relevant, necessary snippets of information to the LLM for each specific task.
-   **No Model Training**: Your data is **never** used to train OpenAI's models. It is only used at the time of the query to provide context.

By combining the power of RAG and LangChain, your AI Engine can now safely and intelligently leverage your own business knowledge to automate tasks with a level of understanding that was previously impossible.