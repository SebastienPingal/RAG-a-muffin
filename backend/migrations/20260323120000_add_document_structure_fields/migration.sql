-- AlterTable
ALTER TABLE "Document"
    ADD COLUMN "extractedBlocks" JSONB,
    ADD COLUMN "chunks" JSONB;
