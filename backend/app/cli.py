import argparse
import asyncio

from sqlalchemy import text

from app.config import get_settings
from app.db import SessionLocal, engine
from app.models import Base
from app.services.ingestion import ingest_reference_deck
from app.services.previews import PreviewRenderError


async def init_database() -> None:
    async with engine.begin() as connection:
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await connection.run_sync(Base.metadata.create_all)
    print("Database initialized.")


async def ingest_references() -> None:
    settings = get_settings()
    paths = sorted(settings.reference_slides_dir.glob("*.pptx"))
    if not paths:
        print(f"No PPTX files found in {settings.reference_slides_dir.resolve()}")
        return

    total = 0
    failures = 0
    async with SessionLocal() as session:
        for path in paths:
            try:
                count = await ingest_reference_deck(session, path)
                total += count
                print(f"Ingested {count} slides from {path.name}", flush=True)
            except (OSError, PreviewRenderError, RuntimeError) as exc:
                await session.rollback()
                failures += 1
                print(f"Skipped {path.name}: {exc}", flush=True)
    print(
        f"Finished: {total} reference slides indexed; {failures} decks skipped.",
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Beautify Slides maintenance commands")
    parser.add_argument("command", choices=["init-db", "ingest-references"])
    args = parser.parse_args()
    asyncio.run(init_database() if args.command == "init-db" else ingest_references())


if __name__ == "__main__":
    main()
