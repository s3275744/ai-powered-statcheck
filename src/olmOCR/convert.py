import os
import shlex
import subprocess
from pathlib import Path

from config import OLMOCR_API_KEY, OLMOCR_MODEL, OLMOCR_SERVER


def run_olmocr(
    input_dir: str | Path,
    output_dir: str | Path,
    server: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
    workers: int = 1,
    max_concurrent_requests: int = 10,
    pages_per_group: int = 2,
) -> None:
    """
    Convert PDFs in input_dir to Markdown using olmOCR via Docker + remote inference.

    Requirements:
      - Docker Desktop installed with WSL2 integration
      - GPU support enabled in Docker
      - Environment variables:
          OLMOCR_SERVER
          OLMOCR_API_KEY
          OLMOCR_MODEL

    The output will be written to:
        output_dir/markdown/*.md
    """

    input_dir = Path(input_dir).resolve()
    output_dir = Path(output_dir).resolve()

    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    server = server or OLMOCR_SERVER
    api_key = api_key or OLMOCR_API_KEY
    model = model or OLMOCR_MODEL

    missing = []
    if not server:
        missing.append("OLMOCR_SERVER")
    if not api_key:
        missing.append("OLMOCR_API_KEY")
    if not model:
        missing.append("OLMOCR_MODEL")

    if missing:
        raise RuntimeError(
            "Missing required configuration: "
            + ", ".join(missing)
        )

    # We mount the common parent so both input and output are visible in the container
    common_parent = Path(os.path.commonpath([input_dir, output_dir]))

    container_mount = Path("/work")
    container_input = container_mount / input_dir.relative_to(common_parent)
    container_output = container_mount / output_dir.relative_to(common_parent)

    pdf_glob = f"{container_input.as_posix()}/*.pdf"

    inner_cmd = (
        f"python -m olmocr.pipeline {shlex.quote(str(container_output))} "
        f"--server {shlex.quote(server)} "
        f"--api_key {shlex.quote(api_key)} "
        f"--model {shlex.quote(model)} "
        f"--markdown "
        f"--workers {workers} "
        f"--max_concurrent_requests {max_concurrent_requests} "
        f"--pages_per_group {pages_per_group} "
        f"--pdfs {pdf_glob}"
    )

    docker_cmd = [
        "docker", "run", "--rm", "--gpus", "all",
        "--entrypoint", "/bin/sh",
        "-v", f"{common_parent}:{container_mount}",
        "alleninstituteforai/olmocr:latest",
        "-c", inner_cmd,
    ]


    print("Running Docker command:")
    print(" ".join(shlex.quote(part) for part in docker_cmd))

    subprocess.run(docker_cmd, check=True)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Convert PDFs to Markdown using olmOCR")
    parser.add_argument("--input_dir", required=True, help="Directory containing PDF files")
    parser.add_argument("--output_dir", required=True, help="Directory for Markdown output")

    args = parser.parse_args()

    run_olmocr(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
    )
