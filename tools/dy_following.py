#!/usr/bin/env python3
"""抓取抖音「关注」列表 —— 用作对标账号候选池

用户的对标池 = 他自己的关注页。抖音站内内容不被搜索引擎完整索引，
网页搜索只能搜到出圈大号，不是同赛道同体量的号。

实测踩过的坑（2026-10-09，全部已验证）：
  1. `?showTab=following` / `?from_tab_name=main&showTab=following`
     —— **都不挂载关注列表**，SPA 只在点击时才渲染。别再用 URL 参数。
  2. 关注列表的卡片类名带哈希后缀（`A_gLREDy` 之类）且会变，不可依赖。
  3. 页面别处的 /user/ 链接（搜索热词、推荐位）会污染结果。
     只认 sec_uid 前缀 `MS4wLjAB`。
  4. 正确做法：进个人页 → **点击「关注 N」这个统计块** → 弹窗里才是关注列表。
  5. 读统计数字时注意：页面的排版是「关注\n5\n粉丝\n67\n获赞\n187」，
     数字在标签**后面**。用「标签在前」的正则会读串位。

用法:
  python tools/dy_following.py
  python tools/dy_following.py --dump    # 找不到时转储弹窗文本用于诊断

输出:
  data/douyin_following.json   关注账号快照
  data/douyin_self.json        本号统计（关注/粉丝/获赞/抖音号/简介）
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
OUT = os.path.join(DATA, "douyin_following.json")
PROFILE = os.path.join(DATA, "douyin_self.json")
URL = "https://www.douyin.com/user/self"
os.makedirs(DATA, exist_ok=True)

# 点击「关注 N」统计块。严格匹配 <标签><数字> 的紧凑结构，避免点到导航里的「关注」。
CLICK_STAT_JS = r"""
() => {
  const norm = (s) => (s || '').replace(/\s+/g, '');
  const cands = [...document.querySelectorAll('div,span,a,p')]
    .filter(e => /^关注\d+$/.test(norm(e.innerText)));
  if (!cands.length) return { ok: false, reason: '没找到「关注N」元素' };
  const el = cands[0];
  el.click();
  return { ok: true, text: norm(el.innerText) };
}
"""

# 弹窗内的关注账号：sec_uid 前缀过滤 + 按出现顺序去重
EXTRACT_JS = r"""
() => {
  const out = new Map();
  for (const a of document.querySelectorAll('a[href*="/user/MS4wLjAB"]')) {
    const href = a.href || '';
    const id = href.split('/user/')[1]?.split('?')[0];
    if (!id) continue;
    const t = (a.innerText || '').trim();
    if (!out.has(id)) out.set(id, { uid: id, href: href, text: t.slice(0, 300) });
    else if (t.length > out.get(id).text.length) out.get(id).text = t.slice(0, 300);
  }
  const body = (document.body.innerText || '').replace(/\n{2,}/g, '\n');
  const m = body.match(/关注\s*\n?\s*(\d[\d.,万]*)\s*\n?\s*粉丝\s*\n?\s*(\d[\d.,万]*)\s*\n?\s*获赞\s*\n?\s*(\d[\d.,万]*)/);
  const idm = body.match(/抖音号[:：]\s*([A-Za-z0-9_.\-]+)/);
  // 简介在「抖音号」行之后、「更多」之前
  const bm = body.match(/抖音号[:：][^\n]*\n([^\n]+)\n/);
  return {
    items: [...out.values()],
    count: out.size,
    following: m ? m[1] : null,
    fans: m ? m[2] : null,
    likes: m ? m[3] : null,
    handle: idm ? idm[1] : null,
    bio: bm ? bm[1].trim() : null,
    bodyTail: body.slice(0, 1500),
  };
}
"""


def main():
    dump = "--dump" in sys.argv[1:]

    with sync_playwright() as pw:
        ctx = launch(pw, USER_DATA, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=90000)
        print("⏳ 等个人页渲染…", flush=True)
        time.sleep(9)

        if "login" in (page.url or ""):
            print("❌ 未登录或登录态已过期。先跑 dy_review_windows.py 登录一次。")
            ctx.close()
            sys.exit(1)

        base = page.evaluate(EXTRACT_JS)
        self_info = {
            "title": page.title(),
            "handle": base.get("handle"),
            "bio": base.get("bio"),
            "following": base.get("following"),
            "fans": base.get("fans"),
            "likes": base.get("likes"),
            "url": page.url,
            "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }
        with open(PROFILE, "w", encoding="utf-8") as f:
            json.dump(self_info, f, ensure_ascii=False, indent=1)
        print(f"本号: {self_info['title']}")
        print(f"  抖音号 {self_info['handle']}")
        print(f"  关注 {self_info['following']} · 粉丝 {self_info['fans']} · 获赞 {self_info['likes']}\n")

        hit = page.evaluate(CLICK_STAT_JS)
        print(f"点击关注统计: {hit}")
        if not hit.get("ok"):
            print("⚠️ 没点到，转储正文前 60 行：")
            for line in base["bodyTail"].split("\n")[:60]:
                if line.strip():
                    print("   ", line.strip()[:90])
            ctx.close()
            sys.exit(1)

        time.sleep(4)
        last, stable, r = -1, 0, {}
        for i in range(12):
            r = page.evaluate(EXTRACT_JS)
            n = r.get("count", 0)
            print(f"   第 {i+1} 轮… 已见 {n}", flush=True)
            if n == last and n > 0:
                stable += 1
                if stable >= 2:
                    break
            else:
                stable = 0
            last = n
            page.mouse.wheel(0, 800)
            time.sleep(1.2)

        items = [x for x in r.get("items", [])]
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=1)

        print(f"\n✅ 抓到 {len(items)} 个关注账号 → {OUT}\n")
        for x in items:
            first = (x["text"].split("\n") or [""])[0].strip()
            print(f"  {first[:34]:<36} {x['uid'][:30]}")

        if not items and dump:
            print("\n=== 弹窗/正文转储 ===")
            print(r.get("bodyTail", "(空)"))

        ctx.close()


if __name__ == "__main__":
    main()
