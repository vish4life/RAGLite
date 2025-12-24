How to run RAGLite app
----------------
1. Clone the repository
2. Install dependencies
    * Backend:
      * install dependencies from requirements.txt  
      ```pipenv install -r requirements.txt```  
      > note: pipenv is used to install python packages here
    * Frontend:
      * run ```npm install``` 
3. download and run ollama services
    * downloand llama3.2, nemotron-3-nano, nemotron-mini, phi3:mini models  
       > ```ollama pull llama3.2```
    * run ollama as per the instructions in the ollama repo  
       > ```brew services start ollama```
4. Run the app as below
    * make sure ollama services are running
    * Backend: `python manage.py runserver 8001` (or any other port other than 8000 as ollama uses 8000 and 11434)
    * Frontend: `npm start`
        * Open ```[http://localhost:3000]``` to view it in your browser.


https://github.com/user-attachments/assets/a4d841b3-a38d-44e7-ac22-d962f422d1b7

# RAGLite Architecture

This document outlines the architecture and operation flows of the RAGLite application.

## 1. Overall System Architecture

The RAGLite application follows a modern decoupled architecture with a React frontend, a Django REST backend, and specialized services for Vector DB (ChromaDB) and LLM (Ollama) integration.

```mermaid
graph TB
    subgraph Frontend ["Frontend (React)"]
        UI[App.js]
        State[React State]
    end

    subgraph Backend ["Backend (Django REST Framework)"]
        Views[views.py - ViewSets]
        Models[models.py - SQLite]
        Utils[utils.py - PDF/Hash]
        
        subgraph Services ["Service Layer"]
            VDB[vectordb_services.py]
            LLM[llm_services.py]
        end
    end

    subgraph Storage ["Storage & External"]
        DB[(SQLite)]
        Chroma[[ChromaDB]]
        Ollama{{Ollama LLM}}
    end

    UI <--> Views
    Views <--> Models
    Views --> Utils
    Views --> VDB
    Views --> LLM
    
    Models <--> DB
    VDB <--> Chroma
    LLM <--> Ollama
```

> [!NOTE]
> The **System Architecture** is largely identical to the Overall Architecture as the backend is a single service handling multiple responsibilities (metadata storage, service orchestration, and vector data management).

---

## 2. Operation Flows

### A. Upload Operation Flow
This flow describes how a document is processed from the moment a user uploads it.

```mermaid
sequenceDiagram
    participant User
    participant App as Frontend (React)
    participant View as DocumentViewSet
    participant Utils as Utils (PDF/Hash)
    participant Chroma as ChromaDB Service
    participant SQLite as SQLite (Metadata)

    User->>App: Select & Upload PDF
    App->>View: POST /ragengine/documents/upload/
    View->>Utils: calculate_hash()
    View->>SQLite: Check for duplicate hash
    
    alt New Document
        View->>SQLite: Create Document entry (Status: Pending)
        View->>Utils: extract_text_from_pdf()
        View->>Utils: chunk_text_by_size()
        View->>Chroma: add_document_chunks()
        View->>SQLite: Update Document entry (Status: Completed)
        View-->>App: 201 Created
    else Duplicate Document
        View-->>App: 200 OK (Existing Document)
    end
```

### B. Query Operation Flow (RAG)
This flow describes the Retrieval-Augmented Generation process when a user asks a question.

```mermaid
sequenceDiagram
    participant User
    participant App as Frontend (React)
    participant View as ChatViewSet
    participant SQLite as SQLite (Cache/History)
    participant Chroma as ChromaDB Service
    participant LLM as LLM Service (Ollama)

    User->>App: Submits Question
    App->>View: POST /ragengine/chats/query/
    View->>SQLite: Check Exact Match (Cache)
    
    alt Cache Hit (SQLite)
        View-->>App: Return Answer
    else Cache Miss (SQLite)
        View->>Chroma: find_similar_question()
        alt Semantic Cache Hit (ChromaDB)
            View-->>App: Return Cached Answer
        else Semantic Cache Miss
            View->>Chroma: search_documents() (Retrieve Context)
            View->>LLM: generate_answer(query, context)
            View->>SQLite: Create Chat entry (History)
            View->>Chroma: add_cached_question() (Save to Cache)
            View-->>App: Return Generated Answer
        end
    end
```

<table>
  <td>Note: The bot image used is generated using Adobe Express. This project is a proof of concept and is not intended for production use.</td>
</table>
