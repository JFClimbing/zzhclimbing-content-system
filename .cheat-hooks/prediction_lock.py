#!/usr/bin/env python3
"""prediction_lock.py — 预测段不可变锁（指纹账本版）

原理：把每份预测的 `## 预测…` 段做 SHA-256 指纹，存进账本。事后任何人改动该段
（包括改标题、改数字、改措辞），verify 都会报 MISMATCH 并 exit 1。

这不是"阻止写入"的强制锁——DSH 的 harness 级拦截需要 dsh-hooks-claude-code 插件，
本项目暂未启用。这是**检测锁**：改不了你的手，但改了一定被抓到。
配合 git history 使用才完整（git 是真正的档案）。

用法：
    python prediction_lock.py lock <file.md> [...]     锁一份或多份（写指纹）
    python prediction_lock.py verify <file.md> [...]   校验
    python prediction_lock.py verify-all               校验 predictions/ 下全部
    python prediction_lock.py status                   看账本
    python prediction_lock.py selftest                 自检（改一下就报错）
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / ".cheat-cache" / "prediction-locks.json"
PREDICTIONS = ROOT / "predictions"

HEADING = re.compile(r"^#{1,6}\s")


def extract_prediction(text: str) -> str | None:
    """Return the first `## …预测…` section, normalized for hashing.

    Normalization: line endings unified, trailing whitespace per line stripped,
    leading/trailing blank lines dropped — so an editor that rewrites line
    endings or trims a stray space does not raise a false alarm. Any change to
    the words, numbers, or heading text does.
    """
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    start = next((i for i, l in enumerate(lines)
                  if HEADING.match(l) and "预测" in l), None)
    if start is None:
        return None
    end = next((j for j in range(start + 1, len(lines))
                if HEADING.match(lines[j])), len(lines))
    body = "\n".join(l.rstrip() for l in lines[start:end])
    return body.strip()


def fingerprint(section: str) -> str:
    return hashlib.sha256(section.encode("utf-8")).hexdigest()


def read_ledger() -> dict:
    if not LEDGER.exists():
        return {}
    try:
        return json.loads(LEDGER.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"账本读取失败: {exc}")
        return {}


def write_ledger(data: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                      encoding="utf-8")


def key_for(path: Path) -> str:
    """Ledger key: path relative to project root when possible, else the name."""
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.name


def cmd_lock(paths: list[str]) -> int:
    ledger = read_ledger()
    rc = 0
    for p in paths:
        path = Path(p)
        if not path.exists():
            print(f"LOCK   {p}: 文件不存在")
            rc = 1
            continue
        section = extract_prediction(path.read_text(encoding="utf-8"))
        if section is None:
            print(f"LOCK   {path.name}: 找不到 `## 预测` 段 — 不是合格预测文件")
            rc = 1
            continue
        k = key_for(path)
        if k in ledger:
            if ledger[k]["sha256"] != fingerprint(section):
                print(f"LOCK   {path.name}: 已锁且指纹不同 — 拒绝覆盖（预测段被改过？）")
                rc = 1
                continue
            print(f"LOCK   {path.name}: 已锁，指纹一致（no-op）")
            continue
        ledger[k] = {
            "sha256": fingerprint(section),
            "bytes": len(section.encode("utf-8")),
            "locked_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        }
        print(f"LOCK   {path.name}: 已锁  {ledger[k]['sha256'][:12]}…")
    write_ledger(ledger)
    return rc


def cmd_verify(paths: list[str]) -> int:
    ledger = read_ledger()
    bad = 0
    for p in paths:
        path = Path(p)
        k = key_for(path)
        if k not in ledger:
            print(f"UNLOCK {path.name}: 无锁记录（先跑 lock）")
            bad += 1
            continue
        if not path.exists():
            print(f"GONE   {path.name}: 文件不在了")
            bad += 1
            continue
        section = extract_prediction(path.read_text(encoding="utf-8"))
        if section is None:
            print(f"BROKEN {path.name}: `## 预测` 段消失 — 预测被删了")
            bad += 1
            continue
        now = fingerprint(section)
        if now == ledger[k]["sha256"]:
            print(f"OK     {path.name}")
        else:
            print(f"MISMATCH {path.name}: 预测段被改过！"
                  f"\n         锁时 {ledger[k]['sha256'][:16]}…"
                  f"\n         现在 {now[:16]}…"
                  f"\n         锁于 {ledger[k]['locked_at']}")
            bad += 1
    return 1 if bad else 0


def cmd_verify_all() -> int:
    files = sorted(PREDICTIONS.glob("*.md")) if PREDICTIONS.is_dir() else []
    if not files:
        print("predictions/ 下没有文件")
        return 0
    return cmd_verify([str(f) for f in files])


def cmd_status() -> int:
    ledger = read_ledger()
    if not ledger:
        print("账本为空 — 还没有锁过任何预测")
        return 0
    print(f"{'文件':<52} {'锁于':<26} 指纹")
    for k in sorted(ledger):
        e = ledger[k]
        print(f"{k[:51]:<52} {e['locked_at']:<26} {e['sha256'][:12]}…")
    print(f"\n共 {len(ledger)} 份已锁")
    return 0


def cmd_selftest() -> int:
    import tempfile
    tmp = Path(tempfile.mkdtemp()) / "t.md"
    tmp.write_text("## 元数据\nx\n## 预测\n播放 5000\n## 复盘\n", encoding="utf-8")
    g = globals()
    g["LEDGER"] = Path(tempfile.mkdtemp()) / "l.json"
    ok = True

    ok &= cmd_lock([str(tmp)]) == 0
    ok &= cmd_verify([str(tmp)]) == 0

    # 改预测段 → 必须 MISMATCH
    tmp.write_text("## 元数据\nx\n## 预测\n播放 500000\n## 复盘\n", encoding="utf-8")
    if cmd_verify([str(tmp)]) == 0:
        print("SELFTEST FAIL: 改了预测段却没报错"); ok = False

    # 只追加复盘段 → 必须仍然 OK
    tmp.write_text("## 元数据\nx\n## 预测\n播放 5000\n## 复盘\n实际 4800\n",
                   encoding="utf-8")
    if cmd_verify([str(tmp)]) != 0:
        print("SELFTEST FAIL: 只追加复盘段却报错"); ok = False

    print("SELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


COMMANDS = {
    "lock": cmd_lock,
    "verify": cmd_verify,
    "verify-all": lambda _: cmd_verify_all(),
    "status": lambda _: cmd_status(),
    "selftest": lambda _: cmd_selftest(),
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(2)
    sys.exit(COMMANDS[sys.argv[1]](sys.argv[2:]))
