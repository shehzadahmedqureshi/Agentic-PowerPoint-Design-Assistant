import shutil
import subprocess
import tempfile
from pathlib import Path

from app.config import get_settings


class PreviewRenderError(RuntimeError):
    pass


def _resolve_executable(configured: str, fallbacks: tuple[str, ...] = ()) -> str:
    configured_path = Path(configured).expanduser()
    if configured_path.is_file():
        return str(configured_path)
    resolved = shutil.which(configured)
    if resolved:
        return resolved
    for fallback in fallbacks:
        fallback_path = Path(fallback).expanduser()
        if fallback_path.is_file():
            return str(fallback_path)
    raise PreviewRenderError(f"Required preview executable not found: {configured}")


def render_pptx_previews(source: Path, destination: Path) -> list[Path]:
    settings = get_settings()
    soffice = _resolve_executable(
        settings.soffice_path,
        (
            "/Applications/LibreOffice.app/Contents/MacOS/soffice",
            "/opt/homebrew/bin/soffice",
            "/usr/local/bin/soffice",
            "~/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/override/soffice",
        ),
    )
    pdftoppm = _resolve_executable(
        settings.pdftoppm_path,
        (
            "/opt/homebrew/bin/pdftoppm",
            "/usr/local/bin/pdftoppm",
            "~/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/override/pdftoppm",
        ),
    )
    destination.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="beautify-slides-") as temporary:
        workdir = Path(temporary)
        profile_uri = (workdir / "libreoffice-profile").as_uri()
        try:
            conversion = subprocess.run(
                [
                    soffice,
                    "--headless",
                    f"-env:UserInstallation={profile_uri}",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(workdir),
                    str(source.resolve()),
                ],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise PreviewRenderError(
                f"LibreOffice timed out while rendering {source.name}"
            ) from exc
        pdf_path = workdir / f"{source.stem}.pdf"
        if conversion.returncode != 0 or not pdf_path.exists():
            message = conversion.stderr.strip() or conversion.stdout.strip()
            raise PreviewRenderError(f"LibreOffice conversion failed: {message}")

        raster = subprocess.run(
            [pdftoppm, "-png", "-r", "144", str(pdf_path), str(workdir / "slide")],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if raster.returncode != 0:
            raise PreviewRenderError(f"PDF rasterization failed: {raster.stderr.strip()}")

        rendered = sorted(
            workdir.glob("slide-*.png"),
            key=lambda item: int(item.stem.rsplit("-", 1)[1]),
        )
        if not rendered:
            raise PreviewRenderError("No slide preview images were generated.")

        copied: list[Path] = []
        for image in rendered:
            target = destination / image.name
            shutil.copy2(image, target)
            copied.append(target)
        return copied
