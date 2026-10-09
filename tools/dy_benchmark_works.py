#!/usr/bin/env python3
"""抓对标候选号最近的作品标题 —— 用来判断"它到底发什么"

只回答一个问题：这个号的定位是不是攀岩教学？所以只取最近 N 条的标题 + 可见数据。

用法:
  python tools/dy_benchmark_works.py            # 每个号取最近 8 条
  python tools/dy_benchmark_works.py --top 5
"""
import json
import os
import sys
import time

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass

from playwright.sync_api import sync_playwright

# 浏览器 channel：跨平台探测。Windows 的 Edge 叫 msedge，macOS / Linux 上
# 一般用 Chrome。可用 DSH_BROWSER_CHANNEL 覆盖（如 chromium / chrome / msedge）。
CHANNEL = os.environ.get("DSH_BROWSER_CHANNEL") or (
    "msedge" if os.name == "nt" else "chrome")


def launch(pw, user_data, headless=False):
    """统一的持久化上下文启动器 —— 全部抓取脚本共用，避免各自复制 channel 逻辑。"""
    return pw.chromium.launch_persistent_context(
        user_data, channel=CHANNEL, headless=headless,
        viewport=None, args=["--start-maximized"],
    )



HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
USER_DATA = os.path.join(ROOT, ".auth-edge")
SRC = os.path.join(DATA, "douyin_benchmark_pool.json")
OUT = os.path.join(DATA, "douyin_benchmark_works.json")

WORKS_JS = r"""
() => {
  const out = [];
  const seen = new Set();
  for (const a of document.querySelectorAll('a[href*="/video/"]')) {
    const href = a.href || '';
    const id = href.split('/video/')[1]?.split('?')[0];
    if (!id || seen.has(id)) continue;
    seen.add(id);
    const t = (a.innerText || a.textContent || '').trim().replace(/\s+/g, ' ');
    out.push({ id: id, text: t.slice(0, 160) });
  }
  return { count: out.length, items: out };
}
"""


def main():
    top = 8
    args = sys.argv[1:]
    if "--top" in args:
        top = int(args[args.index("--top") + 1])

    pool = json.load(open(SRC, encoding="utf-8"))
    result = []

    with sync_playwright() as pw:
        ctx = launch(pw, USER_DATA, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        for n, acct in enumerate(pool, 1):
            name = acct["title"].replace("的抖音 - 抖音", "")
            print("=" * 76)
            print(f"[{n}/{len(pool)}] {name}")
            try:
                page.goto(f"https://www.douyin.com/user/{acct['uid']}",
                          wait_until="domcontentloaded", timeout=60000)
            except Exception as exc:                          # noqa: BLE001
                print(f"   ❌ 导航失败: {exc}")
                continue
            time.sleep(5)
            page.mouse.move(600, 400)
            page.mouse.wheel(0, 900)
            time.sleep(1.5)
            r = page.evaluate(WORKS_JS)
            items = r.get("items", [])[:top]
            print(f"   抓到 {r.get('count', 0)} 条作品链接，展示前 {len(items)} 条:")
            for it in items:
                print(f"     · {it['text'][:88]}")
            print()
            result.append({"name": name, "uid": acct["uid"],
                           "handle": acct.get("handle"), "works": items})
            time.sleep(2)

        ctx.close()

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(f"✅ 已写 {OUT}")


if __name__ == "__main__":
    main()
