#!/usr/bin/env python3
"""Coverage of a Markdown conversion against its source text: words, numbers, corrupt glyphs, per page.
Usage: python3 coverage.py source.txt converted.md [--pages] [--strip REGEX]... [--second other.txt]
source.txt comes from `pdftotext` (pages separated by form feeds), from the OCR text, or from the XML text.
--strip REGEX   remove matches of REGEX from every source line (headers, footers, stamps the script cannot detect)
--second FILE   a second source text (another OCR pass, the embedded layer): per-page agreement with the source"""
import re, sys, unicodedata
from collections import Counter

URL = re.compile(r"https?://[^\s)>\]]+|www\.[^\s)>\]]+")
NUM = re.compile(r"[-\u2212]?\d+(?:[.,]\d+)*")
JOIN = re.compile(r"((?:https?://|www\.)(?:\S*[-/_=?&])?)\n(?=\S)")   # URL broken after a separator
JOIN_DOT = re.compile(r"((?:https?://|www\.)\S*\.)\n(?=[a-z0-9])")                  # URL broken after a dot, next line lower case

def join_urls(text):
    return JOIN_DOT.sub(r"\1", JOIN.sub(r"\1", text))

def prep(text):
    text = join_urls(unicodedata.normalize("NFKC", text)).lower()
    text = text.replace("\x0c", " ").replace("\u00d7", "x").replace("\u2212", "-")
    text = re.sub(r"-\n\s*", "", text)                 # line-end hyphenation
    return URL.sub(" ", text)                          # URLs are counted separately

def words(text):
    text = re.sub(r"(?m)^\s*\d{1,4}\s*$", " ", prep(text))   # bare page numbers
    return re.findall(r"[^\W_\d]+|\d+", text)

def numbers(text):
    return [n.replace(",", ".").lstrip("-") for n in NUM.findall(prep(text))]

def latex(m):                                          # `$` is LaTeX only if it holds LaTeX characters
    return " " if re.search(r"[\\^_{}]", m.group(1)) else m.group(0)

def clean_md(md):
    md = re.sub(r"(?m)^> \*\*(Source|Confidence|Conventions|Residual limitations|Environment):\*\*.*$", "", md)
    md = re.sub(r"(?s)<!--.*?-->", " ", md)            # comments
    md = re.sub(r"</?[a-zA-Z][^>]*>", " ", md)         # real HTML tags only
    md = re.sub(r"(?s)\$\$.*?\$\$", " ", md)
    md = re.sub(r"\$([^$\n]+)\$", latex, md)
    md = re.sub(r"\\([\\`*_{}\[\]()#+\-.!|<>])", r"\1", md)  # un-escape
    return md

def _strip(line, patterns):
    for p in patterns:
        line = re.sub(p, "", line)
    return line

def drop_running(pages, strip):
    """Remove user-given patterns, then lines repeated on many pages (running headers, footers, stamps)."""
    if strip:
        pages = ["\n".join(_strip(l, strip) for l in pg.splitlines()) for pg in pages]
    if len(pages) < 4:
        return pages, 0
    key = lambda l: re.sub(r"\d+", "#", l.strip().lower())
    seen = Counter()
    for pg in pages:
        for k in {key(l) for l in pg.splitlines() if l.strip()}:
            seen[k] += 1
    limit = max(3, int(0.4 * len(pages)))
    running = {k for k, n in seen.items() if n >= limit}
    return ["\n".join(l for l in pg.splitlines() if key(l) not in running) for pg in pages], len(running)

def cov(s, m):
    total = sum(s.values()); missing = s - m
    return total, total - sum(missing.values()), missing, m - s

def pages_of(text):
    pg = text.split("\x0c")
    return pg[:-1] if pg and not pg[-1].strip() else pg

args = sys.argv[1:]
opts = {"strip": [], "second": None, "pages": False}
files = []
i = 0
while i < len(args):
    if args[i] == "--pages": opts["pages"] = True
    elif args[i] == "--strip": opts["strip"].append(args[i + 1]); i += 1
    elif args[i] == "--second": opts["second"] = args[i + 1]; i += 1
    else: files.append(args[i])
    i += 1
raw_src = open(files[0], encoding="utf-8", errors="replace").read()
raw_md = open(files[1], encoding="utf-8", errors="replace").read()
raw_md = re.sub(r"(?s)\A---\n.*?\n---\n", "", raw_md)                       # YAML
src_pages, n_running = drop_running(pages_of(raw_src), opts["strip"])
chunks = re.split(r"<!-- (?:page|slide) \d+ -->", raw_md)
md_pages = chunks[1:] if len(chunks) > 1 else [raw_md]
src, md = "\x0c".join(src_pages), "\n".join(md_pages)

total, found, missing, extra = cov(Counter(words(src)), Counter(words(clean_md(md))))
print(f"WORDS    source {total} | found {found} ({100*found/total:.2f}%) | extra in markdown {sum(extra.values())}")
print(f"         running header/footer lines excluded from the source: {n_running} distinct")
print("         most frequent missing:", ", ".join(f"{w}x{n}" for w, n in missing.most_common(15)))
nt, nf, nmiss, nextra = cov(Counter(numbers(src)), Counter(numbers(clean_md(md))))
print(f"NUMBERS  source {nt} | found {nf} ({100*nf/max(nt,1):.2f}%)")
print("         missing from markdown:", ", ".join(f"{w}x{n}" for w, n in nmiss.most_common(15)))
print("         in markdown but NOT in source (corrupted cells?):", ", ".join(f"{w}x{n}" for w, n in nextra.most_common(40)))
print(f"GLYPHS   U+FFFD in source {raw_src.count(chr(0xFFFD))} | in markdown {raw_md.count(chr(0xFFFD))}")
norm = lambda u: u.rstrip(".,;:)").lower().replace("\\_", "_")
urls_s = {norm(u) for u in URL.findall(join_urls(raw_src))}
urls_m = {norm(u) for u in URL.findall(raw_md)}
print(f"URLS     {len(urls_s & urls_m)} of {len(urls_s)} found")
if opts["pages"]:
    if len(src_pages) != len(md_pages):
        print(f"PAGES    cannot compare: {len(src_pages)} source pages vs {len(md_pages)} markers")
    else:
        bad = []
        for n, (a, b) in enumerate(zip(src_pages, md_pages), 1):
            t, f, _, _ = cov(Counter(words(a)), Counter(words(clean_md(b))))
            if t and 100 * f / t < 99.5:
                bad.append(f"p{n}={100*f/t:.1f}%")
        print("PAGES    below 99.5% word coverage:", ", ".join(bad) if bad else "none")
if opts["second"]:
    sec_pages, _ = drop_running(pages_of(open(opts["second"], encoding="utf-8", errors="replace").read()), opts["strip"])
    if len(sec_pages) != len(src_pages):
        print(f"SECOND   cannot compare: {len(src_pages)} source pages vs {len(sec_pages)} in the second text")
    else:
        bad = []
        for n, (a, b) in enumerate(zip(src_pages, sec_pages), 1):
            ca, cb = Counter(words(a)), Counter(words(b))
            ta, fa, _, _ = cov(ca, cb); tb, fb, _, _ = cov(cb, ca)
            lo = min(100 * fa / ta if ta else 100, 100 * fb / tb if tb else 100)
            if lo < 99.5:
                bad.append(f"p{n}={lo:.1f}%")
        print("SECOND   pages where source and second text agree below 99.5%:", ", ".join(bad) if bad else "none")
