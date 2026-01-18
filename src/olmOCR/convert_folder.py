from pathlib import Path

from convert import run_olmocr


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    input_dir = repo_root / "data" / "input_pdfs"
    output_dir = repo_root / "data" / "output_pdfs"

    print(f"Input PDFs:  {input_dir}")
    print(f"Output dir:  {output_dir}")

    run_olmocr(
        input_dir=input_dir,
        output_dir=output_dir,
        workers=1,
        max_concurrent_requests=10,
        pages_per_group=2,
    )


if __name__ == "__main__":
    main()
