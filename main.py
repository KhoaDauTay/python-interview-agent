from pathlib import Path

output = Path("/Users/khoahuynh/PycharmProjects/python-interview-agent/topics/senior/senior.md")

with output.open("w", encoding="utf-8") as outfile:
    for md_file in sorted(Path("/Users/khoahuynh/PycharmProjects/python-interview-agent/topics/senior").glob("*.md")):
        outfile.write(md_file.read_text(encoding="utf-8"))
        outfile.write("\n\n---\n\n")