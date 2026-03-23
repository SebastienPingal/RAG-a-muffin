-- AlterTable
ALTER TABLE "Collection"
    ADD COLUMN "lastQuestion" TEXT,
    ADD COLUMN "lastAnswer" TEXT,
    ADD COLUMN "lastAnswerTopK" INTEGER,
    ADD COLUMN "lastAnswerMatches" JSONB,
    ADD COLUMN "lastAnsweredAt" TIMESTAMP(3);
