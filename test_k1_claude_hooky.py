"""K1 - Claude Code hooks (R-053, .claude/hooks/fxbot_hooky.py); no network, no price data.

Every check runs the hook as Claude Code does (JSON on stdin, exit code 2 = block / report) against a throwaway git
repository, so the real project and its ledgers are never touched. The test command of the commit gate is replaced
by a tiny script (FXBOT_HOOK_TEST_CMD), so the test suite does not run itself recursively.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
HOOK = PROJECT_ROOT / ".claude" / "hooks" / "fxbot_hooky.py"
SETTINGS = PROJECT_ROOT / ".claude" / "settings.json"

repo = Path(tempfile.mkdtemp(prefix="fxbot_k1_"))
counter = repo.parent / (repo.name + "_runs.txt")


def git(*args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True,
                   env=dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
                            GIT_COMMITTER_EMAIL="t@t"))


def hook(mode, payload, test_exit=0):
    """(exit code, stderr) of one hook call; the fake test command appends one line per run to `counter`."""
    fake = f"{sys.executable} -c \"open(r'{counter}','a').write('x\\n'); raise SystemExit({test_exit})\""
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(repo), FXBOT_HOOK_TEST_CMD=fake)
    r = subprocess.run([sys.executable, str(HOOK), mode], input=json.dumps(payload), capture_output=True, text=True,
                       cwd=repo, env=env, timeout=120)
    return r.returncode, r.stderr


def runs():
    return len(counter.read_text().splitlines()) if counter.exists() else 0


def edit(path):
    return {"tool_name": "Edit", "tool_input": {"file_path": path, "old_string": "a", "new_string": "b"}}


def bash(cmd):
    return {"tool_name": "Bash", "tool_input": {"command": cmd}}


# 0. settings.json is valid and wires the three modes to the hook script
cfg = json.loads(SETTINGS.read_text(encoding="utf-8"))["hooks"]
wired = " ".join(h["command"] for ev in cfg.values() for grp in ev for h in grp["hooks"])
for mode in ("pred-upravou", "pred-prikazem", "po-uprave"):
    assert mode in wired, f"settings.json: chybi rezim {mode}"
assert {g["matcher"] for g in cfg["PreToolUse"]} == {"Edit|Write|MultiEdit|NotebookEdit", "Bash"}

# throwaway repository that looks like the project
(repo / "learning" / "heuristiky" / "predikce").mkdir(parents=True)
(repo / "learning" / "registr_pokusu").mkdir(parents=True)
(repo / "learning" / "heuristiky" / "predikce" / "2026-11-12.jsonl").write_text('{"a": 1}\n')
(repo / "learning" / "registr_pokusu" / "registr.jsonl").write_text('{"a": 1}\n')
(repo / "learning" / "trezor.json").write_text('{"otevreny": false}\n')
(repo / "learning" / "riziko.json").write_text('{"x": 1}\n')
(repo / "modul.py").write_text("x = 1\n")
git("init", "-q")
git("add", "-A")
git("commit", "-q", "-m", "start")

# 1. direct edits: ledgers and vault blocked (relative, absolute, ./ paths, Write of a new month file), others allowed
for p in ("learning/registr_pokusu/registr.jsonl", str(repo / "learning" / "trezor.json"),
          "./learning/heuristiky/predikce/2026-11-12.jsonl", "learning/heuristiky/vyhodnoceni/2026-12.jsonl"):
    code, err = hook("pred-upravou", edit(p))
    assert code == 2 and "BLOCKED" in err, (p, code, err)
code, _ = hook("pred-upravou", {"tool_name": "Write", "tool_input": {"file_path": "learning/heuristiky/predikce/new.jsonl", "content": ""}})
assert code == 2
for p in ("modul.py", "learning/riziko.json", "learning/heuristiky/zive.json", "docs/CHANGE_LOG.md"):
    assert hook("pred-upravou", edit(p))[0] == 0, p

# 2. Bash: writing to the protected files by hand is blocked, reading / scripts / git add are allowed
blocked = [
    "rm -rf learning/heuristiky/predikce",
    "echo '{}' >> learning/registr_pokusu/registr.jsonl",
    "cat x > learning/trezor.json",
    "sed -i 's/a/b/' learning/heuristiky/vyhodnoceni/2026-10-07.jsonl",
    "mv learning/trezor.json /tmp/t.json",
    "cp /tmp/t.json learning/trezor.json",
    "git checkout -- learning/registr_pokusu/registr.jsonl",
    "echo x | tee -a learning/registr_pokusu/registr.jsonl",
    "python3 -c \"open('learning/trezor.json','w').write('{}')\"",
    "python3 - <<'EOF'\nfrom pathlib import Path\nPath('learning/registr_pokusu/registr.jsonl').write_text('')\nEOF",
    f"truncate -s 0 {repo}/learning/registr_pokusu/registr.jsonl",
]
for cmd in blocked:
    code, err = hook("pred-prikazem", bash(cmd))
    assert code == 2 and "BLOCKED" in err, (cmd, code, err)
allowed = [
    "tail -3 learning/registr_pokusu/registr.jsonl | python3 -m json.tool",
    "cat learning/trezor.json",
    "python scripts/heuristiky.py prepocet && python scripts/registr_pokusu.py overit",
    "cp learning/trezor.json /tmp/zaloha.json",
    "grep -c hash learning/heuristiky/predikce/*.jsonl 2>&1",
    "ls -la learning/heuristiky/predikce > /tmp/seznam.txt",
    "rm -rf /tmp/fxbot_x && echo hotovo",
]
for cmd in allowed:
    code, err = hook("pred-prikazem", bash(cmd))
    assert code == 0, (cmd, code, err)

# 3. commit gate: no .py change -> no test run; .py change -> tests run; failing tests block; a passing tree is cached
(repo / "learning" / "riziko.json").write_text('{"x": 2}\n')
assert hook("pred-prikazem", bash("git add learning/ && git commit -m 'uceni -> beze zmeny'"))[0] == 0
assert runs() == 0, "testy bezely bez zmeny .py"
git("add", "-A")
git("commit", "-q", "-m", "data")
(repo / "modul.py").write_text("x = 2\n")
code, err = hook("pred-prikazem", bash("git add -A && git commit -m oprava"), test_exit=1)
assert code == 2 and "failing tests" in err and runs() == 1, (code, err, runs())
assert hook("pred-prikazem", bash("git commit -am oprava"), test_exit=0)[0] == 0 and runs() == 2
assert hook("pred-prikazem", bash("git commit -am oprava"), test_exit=0)[0] == 0 and runs() == 2, "cache nefunguje"
(repo / "novy.py").write_text("y = 1\n")  # untracked .py counts too and changes the tree
assert hook("pred-prikazem", bash("git status && git push"), test_exit=0)[0] == 0 and runs() == 3
assert hook("pred-prikazem", bash("git log --oneline | grep push"), test_exit=1)[0] == 0 and runs() == 3

# 4. after an edit: broken .py / .json / .jsonl reported (exit 2), valid files pass
(repo / "spatne.py").write_text("def f(:\n")
(repo / "spatne.json").write_text("{nejson")
(repo / "spatne.jsonl").write_text('{"a": 1}\n{rozbity\n')
for p in ("spatne.py", "spatne.json", str(repo / "spatne.jsonl")):
    code, err = hook("po-uprave", edit(p))
    assert code == 2 and "broken" in err, (p, code, err)
for p in ("modul.py", "learning/riziko.json", "learning/registr_pokusu/registr.jsonl", "neexistuje.py", "README.md"):
    assert hook("po-uprave", edit(p))[0] == 0, p
assert not list(repo.rglob("__pycache__")), "kontrola syntaxe zapsala __pycache__"

# 5. unreadable input never blocks
r = subprocess.run([sys.executable, str(HOOK), "pred-prikazem"], input="neni json", capture_output=True, text=True)
assert r.returncode == 0

print("K1 OK: hooky chrani deniky a trezor, kontroluji syntaxi a pousti testy pred commitem")
