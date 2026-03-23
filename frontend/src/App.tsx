import { type ChangeEvent, type FormEvent, useEffect, useMemo, useState } from "react";
import { Database, FolderPlus, LoaderCircle, Send, Upload } from "lucide-react";

import "./App.css";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const DEFAULT_USER_ID = 1;

type DocumentItem = {
  id: number;
  name: string;
};

type Collection = {
  id: number;
  name: string;
  userId: number;
  documents?: DocumentItem[] | null;
  createdAt: string;
  updatedAt: string;
};

type CollectionQueryMatch = {
  chunkId: number;
  documentId: number;
  documentName: string;
  chunkIndex: number;
  sectionTitle?: string | null;
  text: string;
  pages: number[];
  tokenCount: number;
  distance: number;
};

type CollectionAnswerResponse = {
  collectionId: number;
  question: string;
  topK: number;
  answer: string;
  matches: CollectionQueryMatch[];
};

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

function formatError(error: unknown) {
  if (error instanceof Error) {
    try {
      const parsed = JSON.parse(error.message) as { detail?: string };
      return parsed.detail ?? error.message;
    } catch {
      return error.message;
    }
  }

  return "Something went wrong.";
}

function App() {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [selectedCollectionId, setSelectedCollectionId] = useState<number | null>(null);
  const [collectionName, setCollectionName] = useState("");
  const [question, setQuestion] = useState("");
  const [topK, setTopK] = useState(5);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadTargetCollectionId, setUploadTargetCollectionId] = useState<number | null>(null);
  const [answer, setAnswer] = useState<CollectionAnswerResponse | null>(null);
  const [isLoadingCollections, setIsLoadingCollections] = useState(true);
  const [isCreatingCollection, setIsCreatingCollection] = useState(false);
  const [isUploadingFile, setIsUploadingFile] = useState(false);
  const [isAskingQuestion, setIsAskingQuestion] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const userCollections = useMemo(
    () => collections.filter((collection) => collection.userId === DEFAULT_USER_ID),
    [collections],
  );

  const uploadTargetCollection =
    userCollections.find((collection) => collection.id === uploadTargetCollectionId) ?? null;

  async function loadCollections(preferredCollectionId?: number) {
    setIsLoadingCollections(true);
    setErrorMessage(null);

    try {
      const data = await apiRequest<Collection[]>("/collections");
      const filteredCollections = data.filter((collection) => collection.userId === DEFAULT_USER_ID);

      setCollections(data);
      setSelectedCollectionId((currentId) => {
        if (preferredCollectionId && filteredCollections.some((item) => item.id === preferredCollectionId)) {
          return preferredCollectionId;
        }

        if (currentId && filteredCollections.some((item) => item.id === currentId)) {
          return currentId;
        }

        return filteredCollections[0]?.id ?? null;
      });
    } catch (error) {
      setErrorMessage(formatError(error));
    } finally {
      setIsLoadingCollections(false);
    }
  }

  useEffect(() => {
    void loadCollections();
  }, []);

  async function handleCreateCollection(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!collectionName.trim()) {
      setErrorMessage("Collection name is required.");
      return;
    }

    setIsCreatingCollection(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const createdCollection = await apiRequest<Collection>("/collections", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: collectionName.trim(),
          userId: DEFAULT_USER_ID,
        }),
      });

      setCollectionName("");
      setSuccessMessage(`Collection "${createdCollection.name}" created.`);
      await loadCollections(createdCollection.id);
    } catch (error) {
      setErrorMessage(formatError(error));
    } finally {
      setIsCreatingCollection(false);
    }
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setSelectedFile(file);
    setSuccessMessage(null);
    setErrorMessage(null);
  }

  async function handleUploadFile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!uploadTargetCollectionId) {
      setErrorMessage("Select a collection first.");
      return;
    }

    if (!selectedFile) {
      setErrorMessage("Choose a file to upload.");
      return;
    }

    setIsUploadingFile(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      await apiRequest(`/collections/${uploadTargetCollectionId}/document/`, {
        method: "POST",
        body: formData,
      });

      setSelectedFile(null);
      setSuccessMessage(`Uploaded "${selectedFile.name}" to the collection.`);
      setUploadTargetCollectionId(null);
      await loadCollections(uploadTargetCollectionId);
    } catch (error) {
      setErrorMessage(formatError(error));
    } finally {
      setIsUploadingFile(false);
    }
  }

  async function handleAskQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedCollectionId) {
      setErrorMessage("Select a collection before asking a question.");
      return;
    }

    if (!question.trim()) {
      setErrorMessage("Enter a question.");
      return;
    }

    setIsAskingQuestion(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const response = await apiRequest<CollectionAnswerResponse>(
        `/collections/${selectedCollectionId}/ask`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            question: question.trim(),
            topK,
          }),
        },
      );

      setAnswer(response);
    } catch (error) {
      setErrorMessage(formatError(error));
    } finally {
      setIsAskingQuestion(false);
    }
  }

  return (
    <main className="app-shell">
      {uploadTargetCollection ? (
        <div
          className="modal-backdrop"
          role="presentation"
          onClick={() => {
            if (!isUploadingFile) {
              setUploadTargetCollectionId(null);
              setSelectedFile(null);
            }
          }}
        >
          <Card
            className="panel modal-card"
            role="dialog"
            aria-modal="true"
            aria-labelledby="upload-dialog-title"
            onClick={(event) => event.stopPropagation()}
          >
            <CardHeader>
              <CardTitle id="upload-dialog-title">Add file</CardTitle>
              <CardDescription>
                Upload into "{uploadTargetCollection.name}".
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form className="stack" onSubmit={handleUploadFile}>
                <label className="file-picker" htmlFor="file-input">
                  <Upload size={18} />
                  <span>{selectedFile ? selectedFile.name : "Choose a document"}</span>
                </label>
                <Input id="file-input" type="file" className="sr-only" onChange={handleFileChange} />
                <div className="modal-actions">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setUploadTargetCollectionId(null);
                      setSelectedFile(null);
                    }}
                    disabled={isUploadingFile}
                  >
                    Cancel
                  </Button>
                  <Button type="submit" disabled={!selectedFile || isUploadingFile}>
                    {isUploadingFile ? <LoaderCircle className="spin" /> : <Upload />}
                    Upload file
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>
      ) : null}

      <section className="hero">
        <div className="hero-copy">
          <div className="hero-badge">
            <Database size={14} />
            <span>RAG workspace</span>
          </div>
          <h1>Build a collection, drop in a file, ask what matters.</h1>
          <p>
            Auth is intentionally bypassed for now. The interface uses the existing backend with
            the default user <strong>#{DEFAULT_USER_ID}</strong>.
          </p>
        </div>
      </section>

      {(errorMessage || successMessage) && (
        <section className="status-row" aria-live="polite">
          {errorMessage ? <p className="status status-error">{errorMessage}</p> : null}
          {successMessage ? <p className="status status-success">{successMessage}</p> : null}
        </section>
      )}

      <section className="workspace-grid">
        <Card className="panel nav-panel">
          <CardHeader>
            <CardTitle>Library</CardTitle>
            <CardDescription>
              {isLoadingCollections
                ? "Loading collections..."
                : `${userCollections.length} available for user #${DEFAULT_USER_ID}.`}
            </CardDescription>
          </CardHeader>
          <CardContent className="nav-panel-content">
            <form className="stack nav-create-form" onSubmit={handleCreateCollection}>
              <Input
                value={collectionName}
                onChange={(event) => setCollectionName(event.target.value)}
                placeholder="New collection"
                aria-label="Collection name"
              />
              <Button type="submit" disabled={isCreatingCollection}>
                {isCreatingCollection ? <LoaderCircle className="spin" /> : <FolderPlus />}
                Create
              </Button>
            </form>

            <div className="tree-list">
              {userCollections.length === 0 ? (
                <div className="empty-state nav-empty-state">
                  <p>No collections yet.</p>
                  <span>Create one to start building your library.</span>
                </div>
              ) : (
                userCollections.map((collection) => {
                  const isActive = collection.id === selectedCollectionId;
                  const documents = collection.documents ?? [];

                  return (
                    <div key={collection.id} className="tree-node">
                      <button
                        type="button"
                        className={`tree-collection${isActive ? " is-active" : ""}`}
                        onClick={() => setSelectedCollectionId(collection.id)}
                      >
                        <span className="tree-marker" aria-hidden="true" />
                        <span className="tree-collection-name">{collection.name}</span>
                        <span className="tree-collection-meta">
                          {documents.length} document{documents.length === 1 ? "" : "s"}
                        </span>
                      </button>

                      <div className="tree-branch" aria-label={`${collection.name} documents`}>
                        {documents.length === 0 ? (
                          <div className="tree-document tree-document-empty">No documents yet</div>
                        ) : (
                          documents.map((document) => (
                            <div key={document.id} className="tree-document">
                              <span className="tree-branch-line" aria-hidden="true" />
                              <span className="tree-document-name">{document.name}</span>
                            </div>
                          ))
                        )}
                        <button
                          type="button"
                          className="tree-add-file"
                          onClick={() => {
                            setSelectedCollectionId(collection.id);
                            setUploadTargetCollectionId(collection.id);
                            setSelectedFile(null);
                            setErrorMessage(null);
                            setSuccessMessage(null);
                          }}
                        >
                          <Upload size={14} />
                          Add file
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </CardContent>
        </Card>

        <div className="main-column">
          <Card className="panel ask-panel">
            <CardHeader>
              <CardTitle>Ask collection</CardTitle>
              <CardDescription>
                Query the indexed chunks and inspect the answer with supporting passages.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form className="stack" onSubmit={handleAskQuestion}>
                <textarea
                  className="question-input"
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  placeholder="What are the key risks called out in this document?"
                  rows={4}
                />
                <div className="ask-controls">
                  <label className="topk-control">
                    <span>Top K</span>
                    <Input
                      type="number"
                      min={1}
                      max={10}
                      value={topK}
                      onChange={(event) => setTopK(Number(event.target.value) || 1)}
                    />
                  </label>
                  <Button
                    type="submit"
                    disabled={!selectedCollectionId || !question.trim() || isAskingQuestion}
                  >
                    {isAskingQuestion ? <LoaderCircle className="spin" /> : <Send />}
                    Ask
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>
      </section>

      <section className="results-grid">
        <Card className="panel answer-panel">
          <CardHeader>
            <CardTitle>Answer</CardTitle>
            <CardDescription>
              {answer ? `Top ${answer.topK} matches used for the response.` : "No answer yet."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {answer ? (
              <div className="answer-body">
                <p>{answer.answer}</p>
              </div>
            ) : (
              <div className="empty-state">
                <p>Ask a question after uploading a document.</p>
                <span>The model response will appear here.</span>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="panel sources-panel">
          <CardHeader>
            <CardTitle>Source chunks</CardTitle>
            <CardDescription>
              Matching passages returned by `/collections/{'{id}'}/ask`.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="match-list">
              {answer?.matches.length ? (
                answer.matches.map((match) => (
                  <article key={match.chunkId} className="match-item">
                    <div className="match-head">
                      <div>
                        <h3>{match.documentName}</h3>
                        <p>
                          chunk #{match.chunkIndex}
                          {match.pages.length ? ` • p. ${match.pages.join(", ")}` : ""}
                          {match.sectionTitle ? ` • ${match.sectionTitle}` : ""}
                        </p>
                      </div>
                      <span className="distance-pill">{match.distance.toFixed(3)}</span>
                    </div>
                    <p>{match.text}</p>
                  </article>
                ))
              ) : (
                <div className="empty-state">
                  <p>No source chunks yet.</p>
                  <span>Relevant passages will appear here after a question is answered.</span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </section>
    </main>
  );
}

export default App;
