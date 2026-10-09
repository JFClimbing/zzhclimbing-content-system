#!/usr/bin/env python3
"""抓自己作品的视频 ID + top 评论 —— cheat-retro 的数据前提

cheat-retro 明确要求：没有评论的复盘 = 看体温计判断病情。
播放数只告诉你"多少人看到"，评论才告诉你"什么内容真的击中了"。

两条路径：
  1. 个人页「作品」tab → 视频 ID（创作者中心的作品列表页不暴露 href）
  2. 每条视频页 → 评论面板 → top 评论（正文 + 赞数）

用法:
  python tools/dy_my_comments.py --limit 4
  python tools/dy_my_comments.py --limit 4 --dump   # 抓不到时转储评论区原文
"""
import json
import os
import re
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
OUT = os.path.join(DATA, "my_video_comments.json")
PROFILE = "https://www.douyin.com/user/self"

IDS_JS = r"""
() => {
  const out = [], seen = new Set();
  for (const a of document.querySelectorAll('a[href*="/video/"]')) {
    const href = a.href || '';
    const id = href.split('/video/')[1]?.split('?')[0];
    if (!id || seen.has(id)) continue;
    seen.add(id);
    out.push({ id: id, text: (a.innerText || '').trim().replace(/\s+/g, ' ').slice(0, 140) });
  }
  return out;
}
"""

# 抖音网页版评论项：data-e2e 钩子优先，其次 class 含 comment 的块。
COMMENTS_JS = r"""
() => {
  const rows = [];
  const nodes = document.querySelectorAll(
    '[data-e2e="comment-item"], div[class*="comment-item"], li[class*="comment"]');
  for (const n of nodes) {
    const t = (n.innerText || '').trim();
    if (!t || t.length < 2) continue;
    const lines = t.split('\n').map(s => s.trim()).filter(Boolean);
    const like = lines.find(s => /^\d+$|^\d+\.\d+万$/.test(s)) || null;
    rows.push({ text: lines.slice(0, 4).join(' | ').slice(0, 220), like: like });
  }
  const panel = document.querySelector('[data-e2e="comment-list"]') ||
                document.querySelector('div[class*="comment"]');
  return {
    count: rows.length,
    rows: rows,
    panelHead: panel ? (panel.innerText || '').replace(/\n{2,}/g, '\n').slice(0, 1200) : null,
  };
}
"""


def main():
    args = sys.argv[1:]
    limit = 4
    if "--limit" in args:
        limit = int(args[args.index("--limit") + 1])
    dump = "--dump" in args

    result = []
    with sync_playwright() as pw:
        ctx = launch(pw, USER_DATA, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        print("① 从个人页取作品 ID…", flush=True)
        page.goto(PROFILE, wait_until="domcontentloaded", timeout=90000)
        time.sleep(8)
        page.mouse.move(600, 400)
        page.mouse.wheel(0, 700)
        time.sleep(2)
        ids = page.evaluate(IDS_JS)
        print(f"   取到 {len(ids)} 条")
        for x in ids[:limit]:
            print(f"     {x['id']}  {x['text'][:60]}")

        for n, x in enumerate(ids[:limit], 1):
            url = f"https://www.douyin.com/video/{x['id']}"
            print(f"\n② [{n}/{min(limit, len(ids))}] {x['id']} 抓评论…", flush=True)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
            except Exception as exc:                          # noqa: BLE001
                print(f"   ❌ 导航失败: {exc}", flush=True)
                continue
            time.sleep(6)
            # 评论区是懒加载的，滚两轮
            for _ in range(3):
                page.mouse.move(1000, 500)
                page.mouse.wheel(0, 500)
                time.sleep(1.2)
            try:
                r = page.evaluate(COMMENTS_JS)
            except Exception as exc:                          # noqa: BLE001
                print(f"   ❌ 读取失败: {exc}", flush=True)
                continue
            print(f"   评论条数: {r['count']}", flush=True)
            for row in r["rows"][:12]:
                print(f"     [{row['like'] or '-'}] {row['text'][:88]}", flush=True)
            if r["count"] == 0 and dump:
                print("   === 评论区原文转储 ===", flush=True)
                print((r["panelHead"] or "(空)")[:900], flush=True)
            result.append({"id": x["id"], "url": url,
                           "list_text": x["text"], "comments": r})
            time.sleep(2)

        ctx.close()

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(f"\n✅ 已写 {OUT}")


if __name__ == "__main__":
    main()
