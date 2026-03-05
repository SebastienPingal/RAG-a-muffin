# RAG Project – Ultra Simple Roadmap

## Objective
Build a simple web app where a user can:
1. Upload documents (PDF or Markdown)
2. Ask questions about those documents
3. Receive answers with **citations from the document**

This project demonstrates core **AI Engineer skills**:
- Document ingestion
- Embeddings
- Vector search
- RAG (Retrieval Augmented Generation)
- API design

---

# Step 1 – Project Setup

## Goal
Create a clean project structure and make sure all services run.

### Tasks
- Create a repository
- Create two folders:
  - `backend/` (FastAPI)
  - `frontend/` (Next.js or simple React)
- Create a `docker-compose` with:
  - Backend service
  - Qdrant (vector database)

### Skills Learned
- FastAPI basics
- Docker compose
- Running a vector database locally

### Expected Result
You can start the backend and access:

```
GET /health
```

The API responds correctly and Qdrant is running.

---

# Step 2 – Upload Documents

## Goal
Allow the user to upload a document and extract its text.

### Tasks
Frontend:
- Create a page with a file upload button

Backend:
- Endpoint:

```
POST /documents
```

- Save the uploaded file
- Extract text from the PDF
- Store document metadata in database

Example table:

```
Document
- id
- filename
- created_at
```

### Libraries
- `pypdf` or `pymupdf`

### Skills Learned
- File upload APIs
- Text extraction from PDFs
- Storing metadata

### Expected Result
User uploads a document and sees confirmation:
- filename
- number of pages
- number of characters extracted

---

# Step 3 – Chunking + Indexing

## Goal
Break documents into small pieces and store them in a vector database.

### Tasks

After extracting the text:

1. Split the document into chunks (500–1000 words).
2. For each chunk store:
   - text
   - document_id
   - page number
   - chunk index

Example structure:

```
Chunk
- id
- document_id
- page
- text
```

3. Generate embeddings for each chunk
4. Store them in Qdrant with metadata

### Skills Learned
- Chunking strategy
- Embeddings
- Vector database basics

### Expected Result
When a document is uploaded:
- The system reports
```
"Document indexed: 84 chunks created"
```

---

# Step 4 – Retrieval (Finding Relevant Text)

## Goal
Find the most relevant chunks for a question.

### Tasks

Create endpoint:

```
POST /ask
```

Input:

```
{
  "document_id": "...",
  "question": "..."
}
```

Process:

1. Convert the question into an embedding
2. Search Qdrant for similar chunks
3. Retrieve top 3–5 results

Return the chunks to the frontend for debugging.

### Skills Learned
- Embeddings for queries
- Similarity search
- Top‑k retrieval

### Expected Result
The system returns relevant passages from the document.

---

# Step 5 – Generate the Final Answer

## Goal
Use the retrieved chunks to generate a response.

### Tasks

1. Build a prompt containing:
   - the question
   - the retrieved chunks

Example:

```
Answer the question using ONLY the context below.

Context:
[chunk1]
[chunk2]
[chunk3]

Question:
...
```

2. Send the prompt to the LLM
3. Return:

```
{
  answer: "...",
  sources: [
    {page: 12, excerpt: "..."},
    {page: 18, excerpt: "..."}
  ]
}
```

### Skills Learned
- Prompt construction
- Structured responses
- Citations

### Expected Result
User asks a question and receives:

- a clear answer
- references to the document

---

# Optional Improvements (For Portfolio)

Add:

### Evaluation Page
- latency
- cost per query
- number of retrieved chunks

### Debug Mode
Display:
- retrieved chunks
- similarity score

### Document Management
- multiple documents
- delete document
- reindex document

---

# Minimal Stack

Backend
- Python
- FastAPI

AI
- OpenAI API (embeddings + generation)

Vector Database
- Qdrant

Frontend
- Next.js or React

Database
- SQLite (MVP)
- Postgres later

---

# Final Result

A working system where:

1. User uploads a document
2. The system indexes it
3. The user asks questions
4. The AI answers with **citations from the document**

This demonstrates a complete **RAG system** suitable for an AI engineer portfolio.

