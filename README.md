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

1. **Plan.** Lists the sources, hashes each file and skips files unchanged since the last run. It **classifies each PDF** (born-digital, scan with a hidden text layer, text layer with defective encoding, line-numbered publisher proof, true scan), detects byte-identical duplicates and files with the same text but different bytes, and shows the method and rough effort. You choose one of three effort **modes** per file or folder (`light`, `performance` or `full`, see [Modes](#modes)); if you don't, it proposes one per file.
2. **Convert** with the right method per type:

   | Type | Method |
   |---|---|
   | Born-digital PDF | `pymupdf4llm` (its built-in OCR switched off), one `<!-- page N -->` marker per page |
   | Scan, or PDF with a hidden OCR layer | Local OCR at 300 dpi; the embedded layer is only an independent cross-check |
   | PDF with defective encoding or margin line numbers | `pdftotext -layout` or a custom PyMuPDF extractor, with symbols restored from page renders |
   | Excel | `openpyxl`, cell by cell, with comments, validation and formatting documented |
   | PowerPoint | `python-pptx`, one section per slide, with speaker notes |
   | Word | `pandoc`, keeping tracked changes, comments and footnotes |

3. **Deterministic fixes (required).** When a value is corrupted and the source itself shows the right one (a lost decimal point, a lost minus sign, a replacement glyph), the agent fixes it and logs the page, the cell, the old and new value and the evidence. It never fixes a value by inference from other numbers.
4. **Verification and confidence.** A page is *verified* when its words are covered at 99.5% or more, every table, formula, figure and number on it was rendered and compared with the source, and it has no unresolved defect. Each file gets a **confidence percentage** (verified pages divided by total pages). **`done` means 100%, nothing else.** Below that the file is `needs review`, with the percentage, the exact list of pages to re-check, and a scope: `minor` (95% or more, or at most 3 pages), `partial` (70 to 94%) or `major` (below 70%). A general, standing limit of the source (no scan can be guaranteed perfect) may be stated and does not block `done`, but a doubt you can locate (a page, a table, a cell) is a defect: that page is not verified and the percentage falls. A bundled script (`coverage.py`, also embedded in the agent file) checks words, numbers (corrupted table cells show up as numbers that are missing or that do not exist in the source), replacement glyphs, URLs and per-page coverage, and can compare the source with a second OCR pass.
5. **Manifest and README.** Writes `manifest.csv` (hash, class, mode, method, tool versions, coverage, pages rendered, fixes applied, confidence, pages to review, status, limitations) and a `README.md` with the document map, conventions, a "not converted yet" list and a changelog.
6. **Stops** and waits for your review.

### Review runs

The agent can also re-verify conversions that already exist: it archives each file first, re-probes its class, applies the fixes and checks of the chosen mode, rewrites the header to the current layout and reports the confidence before and after. If a run is interrupted, each file is left in a consistent state with the pending pages listed.

### Step 2: Concept inventory (only when you ask)

Extracts five tables from the Markdown only: terms, entities, parameters, requirements and cross-references. Every row has the source file, page, line and a verbatim quote that is checked against the Markdown. The agent records what the text says and never interprets it: analysis columns such as status, owner and gap notes stay empty for you to fill.

## Modes

A mode is an **effort plan**. Every mode reports the same confidence percentage, which measures the outcome; the mode decides how much work is spent to raise it. If you don't choose, the agent proposes a mode per file from its class and size.

| Analysis, process or verification | `light` | `performance` | `full` |
|---|---|---|---|
| **Target confidence** | none, reports what it got | 95% or more | 100%, or an honest percentage with the pages left |
| **For** | background reading, search | sources you cite or quote | sources whose numbers, tables, scales or exact wording you reproduce |
| Class probe, hashes, duplicate detection | ✓ | ✓ | ✓ |
| Method chosen by class | ✓ | ✓ | ✓ |
| Headers, footers, heading levels, footnote format | automatic | automatic + spot repairs | ✓ checked against renders |
| Scans: second independent source | ✗ | ✓ | ✓ |
| Deterministic fixes, logged (required in every mode) | scripted only | scripted + every value the checks flag | scripted + every value checked by eye |
| Rebuild broken tables | ✗ | tables flagged by the number check | all |
| Correct OCR misreads | ✗ | words flagged by the dictionary and the second source | all, against renders |
| Reference list: one entry per line, count checked | as converted | ✓ | ✓ entry by entry |
| Page markers = page count; coverage of words, numbers, U+FFFD, per page | ✓ | ✓ | ✓ |
| Reading-order sample (10% of text pages, minimum 2) | ✓ | ✓ | ✓ |
| View the pages flagged by the checks | ✗ | ✓ | ✓ |
| Every page with a table, formula, figure or number | ✗ | viewed at 130 dpi, crops where flagged | cell by cell, crops at 250–300 dpi |
| Every prose page of a scan | ✗ | ✗ | ✓ |
| Pages with headings, labels or pull quotes (markup) | ✗ | ✗ | ✓ viewed |
| Figures | described if cheap, else marked "not described" | described, labels unverified | described and verified |
| **Typical confidence** | 40–80% | 90–99% | 100%, or an honest figure |
| **Rough cost, tokens per page** (earlier runs) | about 0.5k (measured) | about 1.5–2.5k (estimate, not measured) | 2.3k–5.3k (measured; scans cost the most) |

Trade-offs:

| | Strength | What it can leave behind |
|---|---|---|
| `light` | Cheapest. Enough to find what a paper says | Wrong table digits that nobody notices (a paper lost decimal points and still scored 99.8% on words) |
| `performance` | Catches what the scripts can see, for roughly a third of the cost of `full` | Errors the scripts cannot flag: punctuation slips on scans (about one per page on some scans), look-alike digits |
| `full` | The only mode that reliably reaches 100% | Cost. Verifying 324 pages to 100% took about 1.7 million tokens |

The document class matters as much as the mode: a clean born-digital paper costs far less than a scan with many tables, in every mode. `light` can still reach `done` if the file happens to verify to 100%. The cost figures are rough and come from the author's own runs.

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
| `> **[Text inside figure — page N, unverified]** …` | Text pulled out of a vector figure |
| `> *[Image without text content — page N]*`, `> *[Figure not described — page N]*` | Decorative image; meaningful figure left undescribed (light mode) |
| `[?]` | A reading that could not be verified at 250 dpi |
| `Converter notes` | A section for everything the converter wrote (fixes log, OCR corrections, footers), never mixed with source text |
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

Tested on 2026-11-25 in several runs of step 1, each followed by a revision of the instructions:

- **Regulatory sample:** a 7-page PDF and a two-sheet Excel workbook (page markers matched, 183 of 183 cells found verbatim), compared with an earlier manually proofread conversion.
- **Academic bibliography, 23 files (about 700 pages):** born-digital PDFs, older journal articles that are scans with a hidden text layer, a true scan, a text layer with defective encoding, French papers, two Word files, a byte-identical duplicate and a same-text pair with different bytes, in both an early `full` and a `light` mode. Page markers matched the page count on every PDF, and the merged manifest and README were checked against the sources (hashes, sizes, page counts).
- **Review pass on 9 of those files** (324 pages, the `full` effort plan): the agent re-verified them under the confidence rules. Six reached 100% and three stopped at 97%, 87% and 86% with the exact pages left, after 616 logged fixes. This pass found errors that earlier checks had missed (a corrupted table value, blank formulas, a wrongly claimed status).

What those runs showed, and what the current instructions fix: word coverage alone misses corrupted table cells (a lost decimal point passed at 99.8%), the text layer of a scan cannot be trusted, converter defaults can inject OCR noise, and a binary pass/fail status hides whether one page or forty need re-checking. The current version adds the numeric check, the scan policy, required deterministic fixes and the graded confidence score.

**Not yet tested with the current instructions:** the `performance` mode (its cost is an estimate), the final three-mode wording and the residual-doubt rule, step 2 (concept inventory), PowerPoint, and the fallback path without the Python libraries.

**Tip.** Claude Code may start a sub-agent from an older copy of the agent file if you edited it during a session. Start a new session after installing or updating it.

## Limitations

- It has been tested on a sample (see Test status), not on a full project. Review step 1 before asking for step 2.
- Verification is expensive: reaching `done` (100%) in `full` mode means rendering every page with a table, formula, figure or number (see the cost row of the [mode table](#modes)). Use `light` for background reading, `performance` for sources you cite, and read the confidence percentage to decide what still needs a look.
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
