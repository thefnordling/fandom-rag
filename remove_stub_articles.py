import json
from pathlib import Path
import argparse
import sys

STUB_PHRASE = (
    "This article is a <a href=\"/wiki/Category:Stubs\" title=\"Category:Stubs\">stub</a>. You can help Clair Obscur Wiki by"
)


def is_stub_html(html: str) -> bool:
    # Minimal exact-match approach; can be improved later
    return STUB_PHRASE in html


def get_output_path(input_path: Path) -> Path:
    # Insert '-no-stubs' before the file extension
    if input_path.suffix:
        return input_path.with_name(input_path.stem + "-no-stubs" + input_path.suffix)
    else:
        return input_path.with_name(input_path.name + "-no-stubs")


def main():
    parser = argparse.ArgumentParser(description="Remove stub articles from a JSONL file.")
    parser.add_argument("input_file", help="Path to the input JSONL file")
    if len(sys.argv) < 2:
        print("❌ No input file provided.")
        print("Example usage:")
        print("  python remove_stub_articles.py data.jsonl")
        sys.exit(1)
    args = parser.parse_args()
    print(f'wtf: {args.input_file}')

    input_path = Path(args.input_file)
    output_path = get_output_path(input_path)

    if not input_path.exists():
        print(f"❌ Input file not found: {input_path}")
        sys.exit(1)

    kept = 0
    total = 0

    with input_path.open("r", encoding="utf-8") as infile, output_path.open("w", encoding="utf-8") as outfile:
        for line in infile:
            total += 1
            try:
                record = json.loads(line)
                html = record.get("html", "")
                if not is_stub_html(html):
                    outfile.write(json.dumps(record, ensure_ascii=False) + "\n")
                    kept += 1
            except Exception as e:
                print(f"❌ Skipping line {total} due to error: {e}")

    print(f"✅ Removed stub entries. Kept {kept} out of {total} articles.")
    print(f"Output written to: {output_path}")


if __name__ == "__main__":
    main()
