import shutil
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import database_status, get_session
from app.models import TemplateSlide
from app.schemas import HealthResponse, UploadResponse
from app.services.embeddings import embed_descriptions
from app.services.pptx_parser import analyze_presentation
from app.services.previews import PreviewRenderError, render_pptx_previews
from app.services.retrieval import find_similar

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        database=await database_status(),
        groq_configured=bool(settings.groq_api_key),
        reference_directory=str(settings.reference_slides_dir.resolve()),
    )


@router.post("/presentations/analyze", response_model=UploadResponse)
async def analyze_upload(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> UploadResponse:
    filename = Path(file.filename or "upload.pptx").name
    if Path(filename).suffix.lower() != ".pptx":
        raise HTTPException(status_code=415, detail="Only .pptx files are supported.")

    presentation_id = uuid4()
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    destination = settings.uploads_dir / f"{presentation_id}.pptx"
    max_bytes = settings.max_upload_mb * 1024 * 1024

    with destination.open("wb") as output:
        shutil.copyfileobj(file.file, output)
    if destination.stat().st_size > max_bytes:
        destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {settings.max_upload_mb} MB limit.",
        )

    try:
        analysis = analyze_presentation(destination)
        analysis.filename = filename
    except Exception as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail="The PPTX could not be parsed.") from exc

    render_work = settings.previews_dir / f"upload-{presentation_id}"
    try:
        rendered = render_pptx_previews(destination, render_work)
        for slide, rendered_image in zip(analysis.slides, rendered, strict=True):
            preview_name = f"{presentation_id}-slide-{slide.slide_number}.png"
            preview_path = settings.previews_dir / preview_name
            shutil.move(rendered_image, preview_path)
            slide.preview_url = f"/previews/{preview_name}"
    except (OSError, PreviewRenderError) as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Uploaded slide preview generation failed: {exc}",
        ) from exc
    finally:
        shutil.rmtree(render_work, ignore_errors=True)

    matches: dict[int, list] = {}
    try:
        embeddings = embed_descriptions(
            [slide.structural_description for slide in analysis.slides]
        )
        for slide, embedding in zip(analysis.slides, embeddings, strict=True):
            matches[slide.slide_number] = await find_similar(
                session,
                embedding,
                slide.model_dump(mode="json"),
            )
    except (OSError, RuntimeError, SQLAlchemyError):
        # Analysis remains useful before PostgreSQL, the model, or reference slides are ready.
        matches = {}

    return UploadResponse(
        presentation_id=presentation_id,
        analysis=analysis,
        matches=matches,
    )


@router.get("/templates/{template_id}/download")
async def download_template(
    template_id: UUID,
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> FileResponse:
    template = await session.scalar(
        select(TemplateSlide).where(TemplateSlide.id == template_id)
    )
    if template is None:
        raise HTTPException(status_code=404, detail="Reference slide not found.")

    source = (settings.reference_slides_dir / template.source_filename).resolve()
    reference_root = settings.reference_slides_dir.resolve()
    if reference_root not in source.parents or not source.is_file():
        raise HTTPException(status_code=404, detail="Reference PPTX file is unavailable.")
    return FileResponse(
        path=source,
        filename=template.source_filename,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )
