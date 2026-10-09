#!/usr/bin/env python3
"""抖音作品数据 · Windows 一键抓取（Playwright + 系统 Edge）

用法:
  python tools/dy_review_windows.py               # 抓取 + 存快照 + 表格 + 增量 + 对答案
  python tools/dy_review_windows.py --login-only  # 只打开浏览器让你登录，不抓取
  python tools/dy_review_windows.py --diff        # 只看与上次快照的播放增量
  python tools/dy_review_windows.py --table       # 打印全量表格

依赖:
  pip install playwright
  使用系统浏览器（Windows 默认 Edge，macOS/Linux 默认 Chrome），
无需 playwright install 下载 Chromium。可用 DSH_BROWSER_CHANNEL 覆盖。

首次运行会打开 Edge，你需要扫码/验证码登录抖音创作者中心一次；
登录态持久化到 .auth-edge/（已 gitignore），之后可复用，过期需重登。
"""
import json
import os
import re
import sys
import glob
import time
import datetime

# Windows 默认控制台编码 GBK 遇到 emoji 会抛 UnicodeEncodeError，统一转 UTF-8 输出
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
ROOT = os.path.dirname(HERE)                      # 仓库根
DATA = os.path.join(ROOT, "data")
REG = os.path.join(DATA, "prediction_registry.json")
USER_DATA = os.path.join(ROOT, ".auth-edge")      # 本账号独立登录态（与另一个号隔离，gitignore）
URL = "https://creator.douyin.com/creator-micro/content/manage"
os.makedirs(DATA, exist_ok=True)
os.makedirs(USER_DATA, exist_ok=True)

# ⚠️ 字段名会随创作者中心改版变化。实测（2026-10-09）当前版本暴露的是：
#     播放 / 点赞 / 评论 / 分享 / 收藏 / 完播率 / 2秒跳出率 / 吸粉量
# 旧版的「划走率 / 文案展开率 / 平均浏览图片数」已经不存在了 —— 旧字段名会让
# 整列抓成 "-"。改版后再跑 --table，若某列变 "-" 就是又改名了。
METRIC_ORDER = ["播放", "点赞", "评论", "分享", "收藏", "完播率",
                "2秒跳出率", "吸粉量"]

# 滚动加载列表：Douyin 作品列表是懒加载的自定义滚动容器，必须滚它才出卡片
SCROLL_JS = """
() => {
  const list = document.querySelector('div[class*="list-scroll"]')
             || document.querySelector('div[class*="scroll"]');
  if (list) {
    list.scrollTop += 800;
    return list.scrollTop;
  }
  window.scrollBy(0, 800);
  return -1;
}
"""

# 抓取：从卡片提取标题 + 指标标签/值（选择器沿用 ops-manual/数据复盘自动化.md 的结论）
EXTRACT_JS = """
() => {
  const out = [];
  const cards = document.querySelectorAll('div[class*="video-card-content"]');
  for (const c of cards) {
    const titleEl = c.querySelector('[class*="title"]');
    const metrics = {};
    const items = c.querySelectorAll('div[class*="metric-item-container"]');
    for (const it of items) {
      const lab = it.querySelector('div[class*="metric-label"]');
      const val = it.querySelector('div[class*="metric-value"], div[class*="value"]');
      if (lab && val) metrics[lab.innerText.trim()] = val.innerText.trim();
    }
    const head = c.innerText.split('\\n').map(s => s.trim()).filter(Boolean).slice(0, 12);
    const all = c.innerText.split('\\n').map(s => s.trim()).filter(Boolean);
    // 卡片第一行是时长（02:07），日期行形如「2026年10月08日 19:30」
    const duration = all.find(s => /^\\d{1,2}:\\d{2}$/.test(s)) || '';
    const pub = all.find(s => /\\d{4}\\u5e74\\d{1,2}\\u6708\\d{1,2}\\u65e5/.test(s)) || '';
    // 标题元素里混入了「编辑作品/设置权限/删除作品」等悬停菜单文字，只取第一行
    const titleText = (titleEl ? titleEl.innerText : c.innerText).split('\\n')[0].trim();
    out.push({ title: titleText, head: head, metrics: metrics,
               duration: duration, publish_date: pub });
  }
  return { count: cards.length, cards: out };
}
"""


def num(v):
    try:
        return float(str(v).replace("%", "").replace(",", "").replace("万", "0000"))
    except Exception:
        return None


def _wait_login(page, timeout=360):
    """等待登录完成（浏览器可见，用户扫码/验证码）。

    坑：登录成功后抖音会跳到创作者中心**首页**，而不是我们请求的作品管理页。
    原版只等作品卡片的 selector，于是永远等不到、白等到超时。
    修法：一旦发现"已离开登录页且人在 creator.douyin.com"，就重新导航回
    作品管理页，再去找卡片。
    """
    print("⏳ 请在弹出的 Edge 里完成抖音创作者中心登录（扫码 / 验证码）…",
          flush=True)
    deadline = time.time() + timeout
    reentered = False
    while time.time() < deadline:
        if page.query_selector('div[class*="video-card-content"]') or \
           page.query_selector('div[class*="list-scroll"]'):
            print("✅ 已进入作品管理页", flush=True)
            return True
        url = page.url or ""
        if not reentered and "creator.douyin.com" in url and "login" not in url:
            print("✅ 检测到已登录，重新进入作品管理页…", flush=True)
            try:
                page.goto(URL, wait_until="domcontentloaded", timeout=90000)
            except Exception as exc:                      # noqa: BLE001
                print(f"   ⚠️ 重新导航失败：{exc}", flush=True)
            reentered = True
            time.sleep(3)
            continue
        time.sleep(2)
    return False


def scrape(page, rounds=25):
    """真实滚轮滚动 + 抓取，直到卡片数量稳定。

    注意：此列表是自定义滚动容器，window.scrollBy / scrollTop 均无效，
    必须用真实滚轮事件（等价于 minis-browser-use 的 scroll 命令）。
    """
    last = -1
    stable = 0
    for _ in range(rounds):
        vw = page.viewport_size or {"width": 1280, "height": 720}
        page.mouse.move(vw["width"] // 2, vw["height"] // 2)
        page.mouse.wheel(0, 900)
        time.sleep(0.8)
        r = page.evaluate(EXTRACT_JS)
        n = r.get("count", 0)
        if n == last:
            stable += 1
            if stable >= 3 and n > 0:
                break
        else:
            stable = 0
        last = n
    return page.evaluate(EXTRACT_JS)


def parse(cards):
    out = []
    for c in cards:
        title = (c.get("title") or "").split("\n")[0].strip()
        m = {k: c.get("metrics", {}).get(k, "-") for k in METRIC_ORDER}
        out.append({"title": title[:120], "raw": m, "images": None,
                    "date": c.get("publish_date", ""), "duration": c.get("duration", ""),
                    "sched": "", "status": "published", "pinned": False})
    return out


def save(posts):
    today = datetime.date.today().isoformat()
    p = os.path.join(DATA, f"dy_works_{today}.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=1)
    print(f"   💾 已存 {p}")
    return p


def last_snapshot(exclude=None):
    fs = sorted(glob.glob(os.path.join(DATA, "dy_works_*.json")))
    fs = [f for f in fs if f != exclude]
    if not fs:
        return None
    with open(fs[-1], encoding="utf-8") as f:
        return json.load(f)


def print_table(posts):
    print(f"\n{'时长':>6} {'标题':<22}{'播放':>7}{'赞':>6}{'评':>5}{'享':>5}{'藏':>5}"
          f"{'完播率':>9}{'2秒跳出':>9}{'吸粉':>6}  发布日期")
    for p in posts:
        r = p["raw"]
        print(f"{p.get('duration', ''):>6} {p['title'][:22]:<22}{r['播放']:>7}{r['点赞']:>6}"
              f"{r['评论']:>5}{r['分享']:>5}{r['收藏']:>5}"
              f"{r['完播率']:>9}{r['2秒跳出率']:>9}{r['吸粉量']:>6}  {p.get('date', '')}")


def key(p):
    return (p["title"] or "")[:16]


def print_diff(old, new):
    om = {key(p): p for p in old}
    print("\n" + "=" * 72)
    print("📈 与上次快照的差异（播放增量）")
    print("=" * 72)
    for p in new:
        k = key(p)
        if k in om:
            a, b = num(om[k]["raw"]["播放"]), num(p["raw"]["播放"])
            if a is not None and b is not None and b != a:
                print(f"  {p['title'][:26]:<28} {a:>7.0f} → {b:>7.0f}  ({b - a:+.0f})")
        else:
            print(f"  🆕 {p['title'][:30]}  播放 {p['raw']['播放']}")


def auto_check(posts, force=False):
    if not os.path.exists(REG):
        return
    with open(REG, encoding="utf-8") as f:
        reg = json.load(f)
    today = datetime.date.today().isoformat()
    due = [it for it in reg.get("items", [])
           if it["status"] == "pending" and (force or it["check_at"] <= today)]
    if not due:
        return
    print("\n" + "=" * 72)
    print("🎯 自动对答案")
    print("=" * 72)
    for it in due:
        hit = None
        for p in posts:
            if it.get("match") and it["match"] in p["title"]:
                hit = p
                break
        if not hit:
            print(f"\n⏳ {it['title']}  —— 还没发（计划 {it['published']}）")
            continue
        print(f"\n📌 {it['title']}   （对答案日 {it['check_at']}）")
        for mk, pred in it.get("metrics", {}).items():
            act = hit["raw"].get(mk, "-")
            an = num(act)
            ok = ""
            if isinstance(pred, (int, float)) and an is not None:
                dev = (an - pred) / pred * 100
                ok = f"  偏差 {dev:+.1f}%"
                rng = (it.get("range") or {}).get(mk)
                if rng:
                    ok += "  ❌ 出区间" if not (rng[0] <= an <= rng[1]) else "  ✅ 在区间"
            print(f"     {mk:<8} 预测 {str(pred):<8} 实测 {str(act):<8}{ok}")


def main():
    args = sys.argv[1:]
    login_only = "--login-only" in args

    with sync_playwright() as pw:
        ctx = launch(pw, USER_DATA, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=90000)

        if not _wait_login(page):
            print("❌ 等待登录超时（6 分钟）。请重跑本脚本并完成登录。")
            ctx.close()
            sys.exit(1)

        if login_only:
            print("✅ 已登录。登录态已保存，浏览器保持打开，可手动关闭。")
            ctx.close()
            return

        print("📡 正在抓取抖音创作者中心…")
        inner = scrape(page)
        posts = parse(inner["cards"])
        print(f"   ✅ 抓到 {len(posts)} 条作品")
        if not posts:
            print("⚠️ 抓到 0 条 —— 可能登录态过期或页面结构变化，请重登后重试。")
            ctx.close()
            sys.exit(1)

        path = save(posts)

        if "--table" in args or True:
            print_table(posts)

        auto_check(posts, force="--force-check" in args)

        old = last_snapshot(exclude=path)
        if old:
            print_diff(old, posts)

        ctx.close()


if __name__ == "__main__":
    main()
