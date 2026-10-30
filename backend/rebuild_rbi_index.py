import argparse

from backend.app.services.rebuild_rbi_index import build_staged_rbi_index


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build and validate an RBI index in a staging directory."
    )
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    stage_dir, document_count = build_staged_rbi_index(limit=args.limit)
    print(f"Validated staged index: {stage_dir} ({document_count} chunks)")
    print("The active RBI index was not changed.")


if __name__ == "__main__":
    main()
