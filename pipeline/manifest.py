#!/usr/bin/env python3
"""Which files are public: one reading of public_manifest.txt, shared by the gate's checks 20
(tone), 25 (no church name) and 50 (typed counts), and by the notes repo's export to the public
page repo.

A line is a path or glob relative to the repo root. A line starting with "-" marks files that are
public but not tone-scanned (Scripture, the guard's own word list). Text after "#" is a comment.

One matcher decides for everyone (matches()): "*" never crosses a "/" and never matches a name
that starts with ".", like a shell glob. The checks apply it to the files on disk, so a new file is
checked before its first commit; the export applies it to the last commit's tree (committed()),
so exactly what was committed ships. Both therefore see the same set of paths.
"""
import functools, os, re, subprocess

NAME = 'public_manifest.txt'
SKIP_DIRS = {'.git', 'node_modules', '__pycache__'}

def read(root, rev=None):
    """(include patterns, exempt patterns), from the manifest on disk, or as committed in `rev`."""
    # through decode(), so a BOM (PowerShell 5's Set-Content) never sticks to the first pattern
    text = decode(blob(root, NAME, rev) if rev else open(os.path.join(root, NAME), 'rb').read())
    inc, exc = [], []
    for raw in text.splitlines():
        line = raw.split('#', 1)[0].strip()
        if not line:
            continue
        (exc if line.startswith('-') else inc).append(line.lstrip('- ').strip())
    return inc, exc

@functools.lru_cache(maxsize=None)
def _rx(pat):
    out = []
    for seg in pat.split('/'):
        r = ''.join('[^/]*' if c == '*' else '[^/]' if c == '?' else re.escape(c) for c in seg)
        if not seg.startswith('.'):
            r = '(?!\\.)' + r   # a wildcard segment never matches a dot-file, as in a shell
        out.append(r)
    return re.compile('/'.join(out) + r'\Z')

def matches(rel, pats):
    rel = rel.replace('\\', '/')
    return any(_rx(p).match(rel) for p in pats)

def key(rel):
    """One way to compare repo-relative paths: '/' separators, and case-insensitive on Windows
    the way the file system is. Used by the export."""
    return os.path.normcase(rel.replace('\\', '/')).replace('\\', '/')

def ls_files(root, *args):
    """Repo-relative paths from `git ls-files -z ARGS` (raw, so non-ASCII names are not quoted),
    or None when `root` is not a git repo."""
    p = subprocess.run(['git', '-C', root, 'ls-files', '-z', *args], capture_output=True)
    if p.returncode != 0:
        return None
    return [f for f in p.stdout.decode('utf-8').split('\0') if f]

def _split(rels, root, rev=None):
    inc, exc = read(root, rev)
    pub = sorted(r for r in rels if matches(r, inc))
    ex = [r for r in pub if matches(r, exc)]
    return [r for r in pub if r not in ex], ex

def public_rel(root):
    """(to tone-scan, public but exempt): repo-relative paths of the public files on disk."""
    rels = []
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        rels += [os.path.relpath(os.path.join(d, f), root).replace(os.sep, '/') for f in files]
    return _split(rels, root)

def public_files(root):
    """(to tone-scan, public but exempt), absolute paths, sorted: the files on disk."""
    scan, ex = public_rel(root)
    return [os.path.join(root, r) for r in scan], [os.path.join(root, r) for r in ex]

def tree(root, rev='HEAD'):
    """{repo-relative path: git file mode ('100644', '100755', ...)} for commit `rev`, or None
    when there is no such commit."""
    p = subprocess.run(['git', '-C', root, 'ls-tree', '-r', '-z', rev], capture_output=True)
    if p.returncode != 0:
        return None
    out = {}
    for e in p.stdout.decode('utf-8').split('\0'):
        if e:
            meta, path = e.split('\t', 1)
            out[path] = meta.split(' ', 1)[0]
    return out

def committed(root, rev='HEAD'):
    """(to tone-scan, public but exempt): repo-relative paths of the public files in commit `rev`
    (the export's source of truth), sorted by the manifest as committed in `rev` -- never by an
    uncommitted edit of it -- or None when there is no such commit."""
    t = tree(root, rev)
    return None if t is None else _split(list(t), root, rev)

def blob(root, rel, rev='HEAD'):
    """The bytes of `rel` as committed in `rev`."""
    p = subprocess.run(['git', '-C', root, 'cat-file', 'blob', f'{rev}:{rel}'], capture_output=True)
    if p.returncode != 0:
        raise SystemExit(f'git could not read {rev}:{rel}')
    return p.stdout

# Compressed formats whose text cannot be read as bytes, though their first 8 KB may hold no NUL
# (a PDF's header and metadata): PDF, zip (xlsx, docx), gzip, PNG, JPEG, GIF, web fonts.
BINARY_MAGIC = (b'%PDF', b'PK\x03\x04', b'\x1f\x8b', b'\x89PNG', b'\xff\xd8\xff', b'GIF8', b'wOFF', b'wOF2')

def is_binary(raw):
    """True for bytes with no text to read: a known compressed format, or NUL bytes early on
    without a UTF-16 BOM. An empty file, or one holding only a BOM, is text."""
    if raw[:2] in (b'\xff\xfe', b'\xfe\xff'):
        return False
    return b'\0' in raw[:8192] or raw.startswith(BINARY_MAGIC)

def decode(raw):
    """Text of a file's bytes, never empty for a non-empty text file: UTF-8 (BOM allowed), UTF-16
    when it has a BOM (PowerShell 5's `>`); a byte that is not UTF-8 is replaced on its own, so a
    file with one stray byte is still scanned. A binary file (an image, a spreadsheet: NUL bytes and no UTF-16 BOM)
    has no text to read and comes back '' -- check 25 then fails on it, since it cannot be read."""
    if raw[:2] in (b'\xff\xfe', b'\xfe\xff'):
        txt = raw.decode('utf-16', errors='replace')   # a truncated file reads, it does not crash
    elif is_binary(raw):
        return ''
    else:
        # A stray non-UTF-8 byte (PowerShell 5 appends ANSI) becomes U+FFFD on its own; re-reading
        # the whole file as Latin-1 would turn every UTF-8 no-break space into "Â " and put a
        # letter between the words of a name.
        txt = raw.decode('utf-8-sig', errors='replace')
    return txt.replace('\r\n', '\n')   # CRLF files read like LF ones, so a wrapped phrase still matches

def read_texts(paths, root):
    """{relative path: text} for the given absolute paths."""
    return {os.path.relpath(f, root).replace(os.sep, '/'): decode(open(f, 'rb').read()) for f in paths}

def public_texts(root, exempt=False):
    """{relative path: text} for the public files on disk; exempt=True adds the tone-exempt ones."""
    scan, ex = public_files(root)
    return read_texts(scan + (ex if exempt else []), root)
