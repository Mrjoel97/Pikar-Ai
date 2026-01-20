# Pikar AI - Technology Stack

## 1. Overview

Pikar AI leverages a modern and robust technology stack designed for scalability, performance, and seamless integration of AI capabilities. The architecture combines the flexibility of Python for core agent development with the power of Supabase for backend services and Google Cloud for AI models and deployment.

## 2. Core Technologies

### Programming Languages
-   **Python:** Primary language for AI agent development, scripting, and existing FastAPI components.
-   **TypeScript (for Deno/Edge Functions):** Used for Supabase Edge Functions, providing a highly performant and secure backend for API logic.

### AI/ML Framework & Models
-   **Google ADK (Agent Development Kit):** The foundational framework for building, orchestrating, and deploying AI agents.
-   **Google Gemini 1.5 Pro, Google Gemini 1.5 Flash:** Advanced generative AI models from Google, serving as the core intelligence for all AI agents.
-   **Google `text-embedding-004`:** Used for generating embeddings for the Knowledge Vault's RAG system, enabling semantic search capabilities.

### Backend Services
-   **Supabase Edge Functions (Deno/TypeScript):** The primary backend for implementing core business logic, APIs, and AI orchestration, leveraging Deno's performance and security.
-   **FastAPI/Uvicorn:** Utilized for the existing Python-based ADK agent component, providing a high-performance web framework.

### Database
-   **PostgreSQL with `pgvector`:** The central database solution, integrated with Supabase, providing robust relational data storage and advanced vector indexing for efficient RAG operations.

### Authentication
-   **Supabase Auth:** Provides secure and scalable user authentication and authorization services.

### Frontend
-   **React:** The declarative JavaScript library for building dynamic and interactive user interfaces.
-   **TypeScript:** Enhances code quality and maintainability for frontend development.
-   **TailwindCSS:** A utility-first CSS framework for rapid and consistent UI styling.

### Deployment & Infrastructure
-   **Google Cloud Run:** Serverless platform for deploying containerized applications, offering auto-scaling and simplified management.
-   **Terraform:** Infrastructure as Code (IaC) tool used for provisioning and managing Google Cloud resources.

### Real-time Capabilities
-   **Supabase Realtime:** Enables real-time updates and communication within the application, crucial for interactive agent experiences and live dashboards.

### Observability
-   **OpenTelemetry:** Standardized framework for collecting telemetry data (traces, metrics, logs).
-   **Google Cloud Trace:** Distributed tracing service for monitoring application performance and debugging.
-   **Google Cloud Logging:** Centralized logging service for collecting and analyzing application logs.
-   **BigQuery:** Data warehouse for advanced analytics and storage of observability data.
