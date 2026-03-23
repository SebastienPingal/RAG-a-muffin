-- CreateTable
CREATE TABLE "DocumentChunk" (
    "id" SERIAL NOT NULL,
    "documentId" INTEGER NOT NULL,
    "chunkIndex" INTEGER NOT NULL,
    "text" TEXT NOT NULL,
    "sectionTitle" TEXT,
    "pages" JSONB NOT NULL,
    "blockRefs" JSONB NOT NULL,
    "tokenCount" INTEGER NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "DocumentChunk_pkey" PRIMARY KEY ("id")
);

-- Backfill existing document chunks from the JSONB column into row-based storage.
INSERT INTO "DocumentChunk" (
    "documentId",
    "chunkIndex",
    "text",
    "sectionTitle",
    "pages",
    "blockRefs",
    "tokenCount",
    "updatedAt"
)
SELECT
    d."id" AS "documentId",
    COALESCE((chunk.value ->> 'chunkIndex')::INTEGER, chunk.ordinality - 1) AS "chunkIndex",
    COALESCE(chunk.value ->> 'text', '') AS "text",
    NULLIF(chunk.value ->> 'sectionTitle', '') AS "sectionTitle",
    COALESCE(chunk.value -> 'pages', '[]'::jsonb) AS "pages",
    COALESCE(chunk.value -> 'blockRefs', '[]'::jsonb) AS "blockRefs",
    COALESCE((chunk.value ->> 'tokenCount')::INTEGER, 0) AS "tokenCount",
    CURRENT_TIMESTAMP AS "updatedAt"
FROM "Document" d
CROSS JOIN LATERAL jsonb_array_elements(COALESCE(d."chunks", '[]'::jsonb)) WITH ORDINALITY AS chunk(value, ordinality);

-- CreateIndex
CREATE INDEX "DocumentChunk_documentId_idx" ON "DocumentChunk"("documentId");

-- CreateIndex
CREATE UNIQUE INDEX "DocumentChunk_documentId_chunkIndex_key" ON "DocumentChunk"("documentId", "chunkIndex");

-- AddForeignKey
ALTER TABLE "DocumentChunk"
    ADD CONSTRAINT "DocumentChunk_documentId_fkey"
    FOREIGN KEY ("documentId") REFERENCES "Document"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AlterTable
ALTER TABLE "Document" DROP COLUMN "chunks";
