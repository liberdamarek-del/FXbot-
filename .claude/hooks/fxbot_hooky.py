"""Claude Code hooks for FXBOT (R-053, `.claude/settings.json`).

Rules in CLAUDE.md are only context; these hooks enforce three of them:

    pred-upravou   PreToolUse  Edit|Write|MultiEdit|NotebookEdit: no direct edit of the hash-chained ledgers
                   (learning/heuristiky/predikce|vyhodnoceni, learning/registr_pokusu/registr.jsonl) or of the vault
                   (learning/trezor.json). The scripts append to them; a hand edit breaks the chain or opens the vault.
    pred-prikazem  PreToolUse  Bash: the same files must not be removed, moved, overwritten, appended to by hand,
                   edited with sed -i or restored with git; and a `git commit` / `git push` that carries .py changes
                   runs `python fxbot.py test` first (a passing tree is remembered, so the push after the commit
                   does not run the tests again).
    po-uprave      PostToolUse Edit|Write|MultiEdit: syntax of the edited .py file, JSON of .json, every line of .jsonl.

Exit code 2 = block (PreToolUse) or report to Claude (PostToolUse); the reason goes to stderr. Anything the hook cannot
read (no JSON, no git) lets the call through - the hooks are a seatbelt, not the only check (CI runs the tests too).

The Bash check is a pattern match, not a sandbox: it catches the usual commands, not every possible program.

Test: test_k1_claude_hooky.py (`python fxbot.py test k1`). FXBOT_HOOK_TEST_CMD overrides the test command (tests only).
"""

from __future__ import annotations

import hashlib
import json
import os
import py_compile
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

# Protected paths (posix, relative to the project root). A directory entry ends with "/".
CHRANENE = (
    "learning/heuristiky/predikce/",
    "learning/heuristiky/vyhodnoceni/",
    "learning/registr_pokusu/registr.jsonl",
    "learning/trezor.json",
)

DUVOD = {
    "learning/heuristiky/predikce/": "append-only heuristics ledger with a hash chain (CLAUDE.md, R-038): only "
    "scripts/heuristiky.py / aktualizace.py append to it; never edit or delete lines.",
    "learning/heuristiky/vyhodnoceni/": "append-only heuristics ledger with a hash chain (CLAUDE.md, R-038): only "
    "scripts/heuristiky.py / aktualizace.py append to it; never edit or delete lines.",
    "learning/registr_pokusu/registr.jsonl": "append-only trial registry with a hash chain (R-049): register trials "
    "only with `python scripts/registr_pokusu.py registruj ...`.",
    "learning/trezor.json": "the data vault (R-049): it opens only once and only with the user's explicit consent via "
    "`python scripts/trezor.py otevri --souhlas ...`.",
}

TEST_TIMEOUT = 840  # seconds; the hook timeout in settings.json is 900


def _projekt() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()


def _relativni(cesta: str, projekt: Path) -> str:
    """Posix path relative to the project root when the file is inside it, otherwise the normalised path itself."""
    p = Path(cesta)
    if not p.is_absolute():
        p = projekt / p
    p = Path(os.path.normpath(p))
    try:
        return p.relative_to(projekt).as_posix()
    except ValueError:
        return p.as_posix()


def chranena(rel: str) -> str | None:
    """The protected entry `rel` falls under, or None."""
    rel = rel.lstrip("./") if rel.startswith("./") else rel
    for c in CHRANENE:
        if c.endswith("/"):
            if rel.startswith(c) or rel == c.rstrip("/") or f"/{c}" in f"/{rel}":
                return c
        elif rel == c or rel.endswith("/" + c):
            return c
    return None


def _v_textu(text: str) -> str | None:
    """The protected entry mentioned anywhere in a piece of shell text, or None."""
    for c in CHRANENE:
        if c.rstrip("/") in text:
            return c
    return None


# --- Bash ------------------------------------------------------------------------------------------------------------

_ODDELOVACE = re.compile(r"\|\||&&|[;|&\n]")
_PRESMEROVANI = re.compile(r"\d?>{1,2}\|?\s*(\"[^\"]*\"|'[^']*'|[^\s;&|<>]+)")
_PYTHON_ZAPIS = re.compile(
    r"open\([^)]*['\"](w|a|r\+|w\+|a\+|wb|ab)['\"]|write_text|write_bytes|unlink|os\.remove|shutil\.(move|rmtree|copy)"
    r"|\.truncate|\.rename|\.replace\("
)


def _slova(segment: str) -> list[str]:
    try:
        return shlex.split(segment, posix=True)
    except ValueError:
        return segment.split()


def _prikaz(slova: list[str]) -> tuple[str, list[str]]:
    """First real program of a segment (skips VAR=x, sudo, env, command, time) and its arguments."""
    i = 0
    while i < len(slova) and (re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", slova[i]) or slova[i] in ("sudo", "env", "command", "time", "nohup")):
        i += 1
    if i >= len(slova):
        return "", []
    return os.path.basename(slova[i]), slova[i + 1:]


def zakazany_bash(prikaz: str) -> tuple[str, str] | None:
    """(protected entry, what) when the command writes to a protected file by hand, otherwise None."""
    if not _v_textu(prikaz):
        return None
    for m in _PRESMEROVANI.finditer(prikaz):
        cil = m.group(1).strip("'\"")
        c = chranena(cil) or _v_textu(cil)
        if c:
            return c, "shell redirection into it"
    for segment in _ODDELOVACE.split(prikaz):
        c = _v_textu(segment)
        if not c:
            continue
        program, argy = _prikaz(_slova(segment))
        argy_s_cestou = [a for a in argy if _v_textu(a)]
        if program in ("rm", "rmdir", "mv", "truncate", "shred", "unlink", "dd"):
            return c, f"`{program}`"
        if program in ("cp", "install", "rsync", "ln") and argy and _v_textu(argy[-1]):
            return c, f"`{program}` onto it"
        if program == "tee" and argy_s_cestou:
            return c, "`tee` into it"
        if program in ("sed", "perl", "awk", "gawk") and any(a == "-i" or a.startswith("-i") or a.startswith("--in-place") for a in argy):
            return c, f"`{program} -i`"
        if program == "git" and argy:
            sub = [a for a in argy if not a.startswith("-")]
            if sub and sub[0] in ("rm", "mv", "checkout", "restore") and argy_s_cestou:
                return c, f"`git {sub[0]}`"
    # inline Python (python -c / heredoc): checked on the whole command, its code may contain ";" or newlines
    if re.search(r"(^|[\s;&|(])python[0-9.]*\s+(-c\b|-\s*<<|<<)", prikaz) and _PYTHON_ZAPIS.search(prikaz):
        return _v_textu(prikaz), "inline Python that writes or deletes"
    return None


_GIT_COMMIT_PUSH = re.compile(r"\bgit\b[^;&|\n]*\b(commit|push)\b")


def _git(projekt: Path, *argy: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *argy], cwd=projekt, capture_output=True, text=True, env=env, timeout=120)


def zmenene_py(projekt: Path) -> list[str]:
    """.py files changed in the working tree (incl. untracked) or in commits not yet on the remote."""
    soubory: set[str] = set()
    st = _git(projekt, "status", "--porcelain", "--untracked-files=all")
    if st.returncode != 0:
        return []
    for radek in st.stdout.splitlines():
        cesta = radek[3:].split(" -> ")[-1].strip().strip('"')
        if cesta.endswith(".py"):
            soubory.add(cesta)
    zaklad = None
    for kandidat in ("@{u}", "origin/main"):
        if _git(projekt, "rev-parse", "--verify", "--quiet", kandidat).returncode == 0:
            zaklad = kandidat
            break
    if zaklad:
        d = _git(projekt, "diff", "--name-only", f"{zaklad}...HEAD")
        if d.returncode != 0:  # shallow clone without a merge base
            d = _git(projekt, "diff", "--name-only", zaklad, "HEAD")
        if d.returncode == 0:
            soubory.update(x for x in d.stdout.split() if x.endswith(".py"))
    return sorted(soubory)


def otisk_stromu(projekt: Path) -> str | None:
    """Git tree id of the working tree as it would be committed (temporary index, the real one is untouched)."""
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(tmp) / "index"))
        if _git(projekt, "rev-parse", "--verify", "--quiet", "HEAD").returncode == 0:
            if _git(projekt, "read-tree", "HEAD", env=env).returncode != 0:
                return None
        if _git(projekt, "add", "-A", env=env).returncode != 0:
            return None
        w = _git(projekt, "write-tree", env=env)
        return w.stdout.strip() if w.returncode == 0 else None


def _znacka(projekt: Path) -> Path | None:
    g = _git(projekt, "rev-parse", "--git-dir")
    if g.returncode != 0:
        return None
    d = Path(g.stdout.strip())
    return (d if d.is_absolute() else projekt / d) / "fxbot_testy_ok"


def testy_pred_commitem(projekt: Path) -> tuple[bool, str]:
    """(passed, message). Runs the tests only when .py files changed and this exact tree has not passed yet."""
    py = zmenene_py(projekt)
    if not py:
        return True, ""
    strom = otisk_stromu(projekt)
    prikaz = os.environ.get("FXBOT_HOOK_TEST_CMD")
    klic = hashlib.sha256(f"{strom}|{prikaz or ''}".encode()).hexdigest() if strom else None
    znacka = _znacka(projekt)
    if klic and znacka and znacka.exists() and znacka.read_text(encoding="utf-8").strip() == klic:
        return True, ""
    cmd = shlex.split(prikaz) if prikaz else [sys.executable, "fxbot.py", "test"]
    try:
        r = subprocess.run(cmd, cwd=projekt, capture_output=True, text=True, timeout=TEST_TIMEOUT)
    except subprocess.TimeoutExpired:
        return False, f"`python fxbot.py test` did not finish in {TEST_TIMEOUT} s"
    if r.returncode == 0:
        if klic and znacka:
            try:
                znacka.write_text(klic + "\n", encoding="utf-8")
            except OSError:
                pass
        return True, ""
    konec = "\n".join((r.stdout + r.stderr).strip().splitlines()[-25:])
    return False, f"`python fxbot.py test` failed (changed .py: {', '.join(py[:8])}).\n{konec}"


# --- after an edit ---------------------------------------------------------------------------------------------------

def kontrola_souboru(cesta: Path) -> str | None:
    """Error text when the edited file is not valid Python / JSON / JSON lines, otherwise None."""
    if not cesta.is_file():
        return None
    try:
        if cesta.suffix == ".py":
            with tempfile.TemporaryDirectory() as tmp:  # no __pycache__ in the project
                py_compile.compile(str(cesta), cfile=str(Path(tmp) / "x.pyc"), doraise=True)
        elif cesta.suffix == ".json":
            json.loads(cesta.read_text(encoding="utf-8"))
        elif cesta.suffix == ".jsonl":
            for n, radek in enumerate(cesta.read_text(encoding="utf-8").splitlines(), 1):
                if radek.strip():
                    try:
                        json.loads(radek)
                    except json.JSONDecodeError as e:
                        return f"{cesta.name} line {n}: {e}"
    except py_compile.PyCompileError as e:
        return str(e.msg).strip()
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return f"{cesta.name}: {e}"
    return None


# --- entry point -----------------------------------------------------------------------------------------------------

def _cesta_z_vstupu(vstup: dict) -> str | None:
    ti = vstup.get("tool_input") or {}
    return ti.get("file_path") or ti.get("notebook_path") or ti.get("path")


def main(argv: list[str], stdin_text: str) -> int:
    rezim = argv[0] if argv else ""
    try:
        vstup = json.loads(stdin_text) if stdin_text.strip() else {}
    except json.JSONDecodeError:
        return 0
    projekt = _projekt()

    if rezim == "pred-upravou":
        cesta = _cesta_z_vstupu(vstup)
        if not cesta:
            return 0
        c = chranena(_relativni(cesta, projekt))
        if c:
            print(f"BLOCKED by the FXBOT hook: {c} is an {DUVOD[c]} Do not edit it by hand; if the user really wants "
                  f"a change, tell him what and why and let him decide.", file=sys.stderr)
            return 2
        return 0

    if rezim == "pred-prikazem":
        prikaz = (vstup.get("tool_input") or {}).get("command") or ""
        z = zakazany_bash(prikaz)
        if z:
            c, co = z
            print(f"BLOCKED by the FXBOT hook: {co} on {c}. It is an {DUVOD[c]}", file=sys.stderr)
            return 2
        if _GIT_COMMIT_PUSH.search(prikaz):
            try:
                ok, zprava = testy_pred_commitem(projekt)
            except (OSError, subprocess.SubprocessError):
                return 0
            if not ok:
                print(f"BLOCKED by the FXBOT hook: commit / push with failing tests. {zprava}\nFix the cause, run "
                      f"`python fxbot.py test` and only then commit.", file=sys.stderr)
                return 2
        return 0

    if rezim == "po-uprave":
        cesta = _cesta_z_vstupu(vstup)
        if not cesta:
            return 0
        p = Path(cesta) if Path(cesta).is_absolute() else projekt / cesta
        chyba = kontrola_souboru(p)
        if chyba:
            print(f"FXBOT hook: the edited file is broken - {chyba}. Fix it now.", file=sys.stderr)
            return 2
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:], sys.stdin.read()))
