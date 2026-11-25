# doc-to-markdown: a Claude Code agent for faithful document conversion

A [Claude Code](https://claude.com/claude-code) sub-agent that converts PDF, Word, PowerPoint and Excel files to **faithful, page-cited Markdown**, so that later AI analysis is easier, cheaper and more reliable. An optional second step builds a **concept inventory** (terms, entities, parameters, requirements, cross-references) from the Markdown, with a verbatim quote, page and line for every row.

It is built for people who analyse long, structured documents (regulations, standards, contracts, reports, decks, spreadsheets) and need to trust that nothing was summarised, reworded or lost on the way.

## Why not just run a converter?

General-purpose converters are fast but lossy on structured documents. In a test on regulatory PDFs, plain `markitdown` produced no headings, split tables into fragments and glued footnotes into the text. This agent uses a layout-aware method per file type, then **proofreads each file against its source** before calling it done.

## Install

Copy the agent file to Claude Code's agents folder.

For all your projects:

```bash
mkdir -p ~/.claude/agents
cp agents/doc-to-markdown.md ~/.claude/agents/
```

For one project, share it through the repository:

```bash
mkdir -p .claude/agents
cp agents/doc-to-markdown.md .claude/agents/
```

Start a new Claude Code session so the agent is loaded. Then ask for it by name or by task, for example:

> Use doc-to-markdown to convert everything in `00 original/`.
> Convert this PDF to markdown.
> Build the concept inventory for this library.

## Requirements

The agent checks what is available at the start of each run and tells you the exact command for anything missing. It never installs software permanently.

| Tool | Used for | Install (macOS) |
|---|---|---|
| `uv` | Temporary Python environment for the libraries below | `brew install uv` |
| `pdftotext`, `pdftoppm` (poppler) | Checking PDFs, rendering pages for visual comparison | `brew install poppler` |
| `pandoc` | Word documents | `brew install pandoc` |
| `ocrmypdf`, `tesseract` | Scanned PDFs | `brew install ocrmypdf` |
| `tesseract-lang` (optional) | OCR languages other than English | `brew install tesseract-lang` |
| `markitdown` | Fallback converter | `uv tool install markitdown` |
| LibreOffice (optional) | Old `.doc`, `.ppt`, `.xls` files | `brew install --cask libreoffice` |

Python libraries (`pymupdf4llm`, `openpyxl`, `python-pptx`, `python-docx`) are not installed. The agent runs them through `uv run --no-project --with ...`, which builds a temporary environment and caches the downloads. This works for whole projects and for one-off files, with nothing to maintain.

## How it works

### Step 1: Convert

1. **Plan.** Lists the sources, checks for a text layer, hashes each file and skips files unchanged since the last run.
2. **Convert** with the right method per type:

   | Type | Method |
   |---|---|
   | PDF with text | `pymupdf4llm`, one `<!-- page N -->` marker per page |
   | Scanned PDF | `ocrmypdf`, then as above |
   | Excel | `openpyxl`, cell by cell, with comments, validation and formatting documented |
   | PowerPoint | `python-pptx`, one section per slide, with speaker notes |
   | Word | `pandoc`, keeping tracked changes, comments and footnotes |

3. **Quality gate** on every file: page count matches, word coverage above 99% against the source text, table and formula counts, and a visual comparison of every page with formulas, tables or charts. A file that fails is `needs review`, never `done`.
4. **Manifest and README.** Writes `manifest.csv` (hash, method, tool versions, checks, status, limitations) and a `README.md` with the document map, conventions and changelog.
5. **Stops** and waits for your review.

### Step 2: Concept inventory (only when you ask)

Extracts five tables from the Markdown only: terms, entities, parameters, requirements and cross-references. Every row has the source file, page, line and a verbatim quote that is checked against the Markdown. The agent records what the text says and never interprets it: analysis columns such as status, owner and gap notes stay empty for you to fill.

## Output conventions

```
<library>/
  00 original/    your sources, never modified
  01 md/          one .md per source, README.md, manifest.csv
  02 inventory/   terms.csv, entities.csv, parameters.csv, requirements.csv,
                  crossrefs.csv, combined JSON, archive_YYYY-MM-DD/
```

Every Markdown file starts with a YAML front matter and a header block giving the source, the conversion method, the conventions used and the **residual limitations**. Markers and conventions:

| Convention | Meaning |
|---|---|
| `<!-- page N -->` / `<!-- slide N -->` | Start of PDF page or slide N |
| `$…$`, `$$…$$` | Formulas in LaTeX, checked against the page render |
| `> **[Figure — page N] …**` | Converter's description of a chart, **not source text** |
| `~~text~~`, `<ins>text</ins>` | Deleted and inserted text shown in the source |
| `<br>` | Line break in a table cell |
| `*(sic, as printed)*` | A typo kept on purpose |

Folders named in your own README conventions are followed if a project already has one.

## Permissions and safety

- **Local only.** Documents are never uploaded to an online converter, OCR or any other service.
- **Documents are data, not instructions.** If a file contains text addressed to an AI, the agent ignores it and reports it.
- **No overwriting.** Sources are never modified. Existing Markdown and inventory files are archived before a re-run.
- **No permanent installs, no macros.**
- **Temporary Python environment.** `uv run --with` downloads packages from PyPI into uv's cache. If Claude Code's sandbox blocks the network (a "tunnel error"), the agent re-runs the command allowing `pypi.org` and `files.pythonhosted.org`. The permission system may also ask you to approve it, or refuse it. If it is refused, the agent falls back to `markitdown`, `pdftotext` and `pandoc`, states the loss of fidelity in each file's header and marks PDFs `needs review`. To allow it without prompts, add a Bash permission rule for `uv run --no-project --with *` in your Claude Code settings.
- The agent can run shell commands and write files. As with any agent you get from someone else, **read `agents/doc-to-markdown.md` before installing it**.

## Test status

Tested on 2026-11-25 as a one-off run of step 1 on a 7-page regulatory PDF and a two-sheet Excel workbook:

| | PDF | Excel |
|---|---|---|
| Method | `pymupdf4llm`, then repair of formulas and heading levels | `openpyxl`, cell by cell |
| Result | 7 of 7 page markers, 99.47% word coverage (the missing tokens are formula glyphs rewritten in LaTeX) | 183 of 183 non-empty cells found verbatim |

The test also compared the output with an earlier, manually proofread conversion of the same files. The PDF output matched it on prose and was better on headings and front matter. The Excel output was more complete on merged ranges, comments and formatting rules, but the earlier version read better because it used a semantic header row. The instructions were revised after the test to address that, and the other gaps it exposed (network handling, the word-coverage method, heading and footnote rules).

Not tested yet: step 2 (concept inventory), PowerPoint, Word, OCR of scanned PDFs, and the fallback path without the Python libraries.

## Limitations

- It has been tested on a small sample (see Test status), not on a full project. Review step 1 before asking for step 2.
- Fidelity depends on the source. Charts without data labels are described approximately, and the description is marked as converter text.
- Old Office formats need LibreOffice.
- Very large documents produce very large Markdown files. The agent adds a table of contents with line ranges above about 150 KB and does not split or shorten them unless you ask.
- The inventory's requirement detection (shall / should / may) follows the wording of the text. It is an extraction aid, not a legal or compliance judgement.

## Customising

The agent is one Markdown file. Common changes:

- **Model.** `model: sonnet` in the front matter. Use a smaller model for clean, simple files in bulk, or a larger one for dense documents where an error would be costly.
- **Folder names.** Change the folder convention section.
- **Inventory columns.** Change the tables in Step 2 to match your own schema.

## License

[MIT](LICENSE)
