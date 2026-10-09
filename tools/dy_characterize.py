#!/usr/bin/env python3
"""给关注列表里的每个号做画像 —— 昵称 / 抖音号 / 简介 / 数据 / 作品数

对标账号的选法不是"粉丝最多的"，而是"你想做成它那样的"。所以先把每个号的
定位读出来，再决定导谁。

用法:
  python tools/dy_characterize.py            # 读 data/douyin_following.json
  python tools/dy_characterize.py --limit 10 # 只读前 N 个

输出:
  data/douyin_benchmark_pool.json
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

try:
    from playwright.sync_api import sync_playwright


except ImportError:
    print("❌ 缺少 playwright。请先运行：pip install playwright")
    sys.exit(1)

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
SRC = os.path.join(DATA, "douyin_following.json")
OUT = os.path.join(DATA, "douyin_benchmark_pool.json")

INFO_JS = r"""
() => {
  const body = (document.body.innerText || '').replace(/\n{2,}/g, '\n');
  const lines = body.split('\n').map(s => s.trim()).filter(Boolean);
  const m = body.match(/关注\s*\n?\s*(\d[\d.,万]*)\s*\n?\s*粉丝\s*\n?\s*(\d[\d.,万]*)\s*\n?\s*获赞\s*\n?\s*(\d[\d.,万]*)/);
  const idm = body.match(/抖音号[:：]\s*([A-Za-z0-9_.\-]+)/);
  // 简介：抖音号行之后那一行
  let bio = null;
  const i = lines.findIndex(l => /^抖音号[:：]/.test(l));
  if (i >= 0 && i + 1 < lines.length) bio = lines[i + 1];
  // 作品数：出现的「作品」后面的数字
  const wm = body.match(/作品\s*\n?\s*(\d[\d.,万]*)/);
  return {
    title: document.title,
    handle: idm ? idm[1] : null,
    bio: bio,
    following: m ? m[1] : null,
    fans: m ? m[2] : null,
    likes: m ? m[3] : null,
    works: wm ? wm[1] : null,
    url: location.href,
  };
}
"""


def main():
    args = sys.argv[1:]
    limit = 20
    if "--limit" in args:
        limit = int(args[args.index("--limit") + 1])

    with open(SRC, encoding="utf-8") as f:
        pool = json.load(f)[:limit]

    out = []
    with sync_playwright() as pw:
        ctx = launch(pw, USER_DATA, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        for n, item in enumerate(pool, 1):
            url = f"https://www.douyin.com/user/{item['uid']}"
            print(f"[{n}/{len(pool)}] {url}", flush=True)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
            except Exception as exc:                          # noqa: BLE001
                print(f"   ❌ 导航失败: {exc}", flush=True)
                continue
            time.sleep(5)
            try:
                info = page.evaluate(INFO_JS)
            except Exception as exc:                          # noqa: BLE001
                print(f"   ❌ 读取失败: {exc}", flush=True)
                continue
            info["uid"] = item["uid"]
            out.append(info)
            print(f"   昵称: {info['title']}", flush=True)
            print(f"   抖音号: {info['handle']}   粉丝 {info['fans']} · 获赞 {info['likes']} · 作品 {info['works']}", flush=True)
            print(f"   简介: {(info['bio'] or '(无)')[:110]}", flush=True)
            print(flush=True)
            time.sleep(2)

        ctx.close()

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"✅ 已写 {OUT}（{len(out)} 个号）")


if __name__ == "__main__":
    main()
