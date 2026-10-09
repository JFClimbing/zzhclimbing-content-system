#!/usr/bin/env python3
"""抓对标账号每条视频的完整数据 → samples/<账号名>/<video-id>/meta.md

为什么不用列表页的数字：列表页只暴露播放量。要点赞/评论/收藏/分享必须进视频页。
同时核对作者昵称——列表页的提取会被推荐位污染，进视频页才能确认这条真是这个号的。

用法:
  python tools/dy_sample_metrics.py --account 梦幻拍档 --limit 6
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
SAMPLES = os.path.join(ROOT, "samples")
USER_DATA = os.path.join(ROOT, ".auth-edge")
WORKS = os.path.join(DATA, "douyin_benchmark_works.json")

# 优先用 Douyin 自己的 data-e2e 钩子；拿不到再退回正则扫正文。
PROBE_JS = r"""
() => {
  const pick = (sel) => {
    const el = document.querySelector(sel);
    if (!el) return null;
    const t = (el.innerText || el.textContent || '').trim();
    return t || null;
  };
  const e2e = {};
  for (const k of ['like', 'comment', 'collect', 'share', 'play']) {
    e2e[k] = pick('[data-e2e="video-' + k + '-count"]') ||
             pick('[data-e2e*="' + k + '"]');
  }
  const body = (document.body.innerText || '').replace(/\n{2,}/g, '\n');
  const author =
    pick('[data-e2e="video-author-name"]') ||
    pick('[data-e2e="user-name"]') ||
    pick('h1') || null;
  // 正文里的数字标签（用于兜底 + 诊断）
  const grab = (label) => {
    const m = body.match(new RegExp('([\\d.,]+\\s*[万w]?)\\s*\\n?\\s*' + label));
    return m ? m[1].trim() : null;
  };
  return {
    url: location.href,
    title: document.title,
    author,
    e2e,
    like: grab('点赞'), comment: grab('评论'), collect: grab('收藏'), share: grab('分享'),
    bodyHead: body.slice(0, 900),
  };
}
"""

# 视频页正文里的文案通常就是标题/描述，取「作品」区第一段
CAPTION_JS = r"""
() => {
  const el = document.querySelector('[data-e2e="video-desc"]') ||
             document.querySelector('h1') ||
             document.querySelector('[data-e2e="detail-video-desc"]');
  return el ? (el.innerText || '').trim() : null;
}
"""


def main():
    args = sys.argv[1:]
    account = "梦幻拍档"
    if "--account" in args:
        account = args[args.index("--account") + 1]
    limit = 6
    if "--limit" in args:
        limit = int(args[args.index("--limit") + 1])

    works = json.load(open(WORKS, encoding="utf-8"))
    target = next((a for a in works if account in a["name"]), None)
    if target is None:
        print(f"❌ 在 {WORKS} 里找不到账号 {account}")
        sys.exit(1)

    outdir = os.path.join(SAMPLES, account)
    os.makedirs(outdir, exist_ok=True)

    rows = []
    with sync_playwright() as pw:
        ctx = launch(pw, USER_DATA, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        for n, w in enumerate(target["works"][:limit], 1):
            url = f"https://www.douyin.com/video/{w['id']}"
            list_plays = (re.match(r"\s*(?:置顶\s*)?([\d.]+万?)", w["text"]) or [None, None])[1]
            print(f"[{n}/{min(limit, len(target['works']))}] {w['id']}  列表页播放={list_plays}", flush=True)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
            except Exception as exc:                          # noqa: BLE001
                print(f"   ❌ 导航失败: {exc}", flush=True)
                continue
            time.sleep(6)
            try:
                r = page.evaluate(PROBE_JS)
                cap = page.evaluate(CAPTION_JS)
            except Exception as exc:                          # noqa: BLE001
                print(f"   ❌ 读取失败: {exc}", flush=True)
                continue

            print(f"   标题: {r['title']}", flush=True)
            print(f"   作者: {r['author']}", flush=True)
            print(f"   e2e : {r['e2e']}", flush=True)
            print(f"   正则: 赞={r['like']} 评={r['comment']} 藏={r['collect']} 享={r['share']}", flush=True)
            print(f"   文案: {(cap or '')[:100]}", flush=True)
            print(flush=True)

            d = os.path.join(outdir, w["id"])
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "meta.md"), "w", encoding="utf-8") as f:
                f.write("\n".join([
                    f"# {w['id']}",
                    "",
                    f"- 视频页: {url}",
                    f"- 页面标题: {r['title']}",
                    f"- 作者（视频页实测）: {r['author']}",
                    f"- 列表页播放: {list_plays}",
                    f"- 列表页原始文本: {w['text']}",
                    "",
                    "## 数据",
                    "",
                    "| 指标 | 视频页 e2e | 正文正则 |",
                    "|---|---|---|",
                    f"| 点赞 | {r['e2e'].get('like')} | {r['like']} |",
                    f"| 评论 | {r['e2e'].get('comment')} | {r['comment']} |",
                    f"| 收藏 | {r['e2e'].get('collect')} | {r['collect']} |",
                    f"| 分享 | {r['e2e'].get('share')} | {r['share']} |",
                    f"| 播放 | {r['e2e'].get('play')} | （视频页不显示） |",
                    "",
                    "## 文案",
                    "",
                    "```",
                    (cap or "(未取到)"),
                    "```",
                    "",
                    "## 页面正文开头（诊断用）",
                    "",
                    "```",
                    r["bodyHead"],
                    "```",
                ]) + "\n")
            rows.append({"id": w["id"], "url": url, "probe": r, "caption": cap})
            time.sleep(2)

        ctx.close()

    with open(os.path.join(DATA, "benchmark_sample_metrics.json"), "w",
              encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    print(f"✅ {len(rows)} 条 → {outdir} + data/benchmark_sample_metrics.json")


if __name__ == "__main__":
    main()
