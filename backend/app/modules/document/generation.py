from collections.abc import Sequence

from openai import AsyncOpenAI

from app.core.config import settings


def _format_context(matches: Sequence[dict]) -> str:
    sections: list[str] = []
    for index, match in enumerate(matches, start=1):
        pages = ", ".join(str(page) for page in match.get("pages", [])) or "unknown"
        header = (
            f"[Chunk {index}] "
            f"document={match['documentName']} "
            f"chunkIndex={match['chunkIndex']} "
            f"pages={pages}"
        )
        if match.get("sectionTitle"):
            header += f" section={match['sectionTitle']}"

        sections.append(f"{header}\n{match['text']}")

    return "\n\n".join(sections)


async def answer_with_context(question: str, matches: Sequence[dict]) -> str:
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is required to generate answers")
    if not matches:
        raise ValueError("At least one retrieved chunk is required to generate an answer")

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    context = _format_context(matches)

    response = await client.responses.create(
        model=settings.OPENAI_CHAT_MODEL,
        instructions=(
            "Answer the user using only the provided context. "
            "If the context is insufficient, say that clearly. "
            "Be concise and factual."
        ),
        input=(
            f"Question:\n{question}\n\n"
            f"Context:\n{context}\n\n"
            "Return a direct answer."
        ),
    )
    return response.output_text
