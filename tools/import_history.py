#!/usr/bin/env python3
"""历史导入（cheat-init Phase 3.5）—— 把已抓到的作品建成 videos/ + reconstructed 预测

注意：reconstructed 预测**不计入 calibration_samples**。它们不是盲预测，
只是给 cheat-seed 做"你过去做过什么"的 context。

用法:
  python tools/import_history.py
"""
import hashlib
import json
import os
import sys
from datetime import date

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
VIDEOS = os.path.join(ROOT, "videos")
PREDS = os.path.join(ROOT, "predictions")
MEMO = os.path.join(ROOT, "rubric-memo.md")

# 抓取快照日。真实发布日没能从创作者中心抓出来（列表页没渲染日期列），
# 所以文件名用快照日 + 明确标注 date_source。
SNAPSHOT = "2026-10-09"

# 7 维打分（0-5）。这是"事后反推"的评分——明确非盲、非校准用途。
# 键 = 快照 JSON 里的下标（0 起）。
SCORES = {
    0: dict(ER=3, HP=4, QL=3, NA=3, AB=4, SR=2, SAT=3,
            why="检查向内容，「你还敢用吗」是强钩子，但只给了一个可执行阈值"
                "（工作面磨损达直径 1/4），其余偏笼统提醒。"),
    1: dict(ER=4, HP=4, QL=4, NA=4, AB=5, SR=2, SAT=3,
            why="先破「没有一把主锁是万能的」这个误区，再按 D/H/O 型对应场景，"
                "可直接照做。选型是每个买锁的人都会遇到的问题（AB 拉满）。"),
    2: dict(ER=4, HP=3, QL=4, NA=3, AB=4, SR=2, SAT=5,
            why="「玩攀岩两年，锁门我总算搞清楚了」是强人格叙事，"
                "两条踩坑经验（回半圈 / 自动锁≠绝对安全）很具体。"
                "但标题是个人叙事，钩子强度弱于后果威胁型。"),
    3: dict(ER=5, HP=4, QL=5, NA=5, AB=5, SR=2, SAT=3,
            why="形状→受力逻辑→适用场景→致命误用，原理讲到能自己推陌生场景。"
                "完整度高，四个维度接近满分。"),
}


def short_of(title):
    t = title.split("？")[0].split("?")[0].split("，")[0].strip()
    return t[:8]


def vid_of(title):
    return hashlib.sha256(title.encode("utf-8")).hexdigest()[:12]


def main():
    src = os.path.join(DATA, f"dy_works_{SNAPSHOT}.json")
    posts = json.load(open(src, encoding="utf-8"))

    os.makedirs(VIDEOS, exist_ok=True)
    os.makedirs(PREDS, exist_ok=True)

    made = []
    for i, p in enumerate(posts):
        title = p["title"]
        vid = vid_of(title)
        short = short_of(title)
        stem = f"{SNAPSHOT}_{vid}_{short}"
        vdir = os.path.join(VIDEOS, stem)
        os.makedirs(vdir, exist_ok=True)

        open(os.path.join(vdir, ".gitkeep"), "w").close()

        raw = p["raw"]
        report = [
            f"# {title[:60]}",
            "",
            f"- **video id**: `{vid}`",
            f"- **来源**: 抖音创作者中心作品管理页快照 `data/dy_works_{SNAPSHOT}.json`",
            f"- **发布日**: ⚠️ 未取到（列表页日期列没渲染），文件名用的是**抓取日** {SNAPSHOT}",
            "- **原稿**: `script_lost` —— 用户未提供，且图文/视频原稿未存档",
            "",
            "## 实绩数据（抓取于 " + SNAPSHOT + "）",
            "",
            "| 指标 | 值 |",
            "|---|---|",
        ]
        for k, v in raw.items():
            report.append(f"| {k} | {v} |")
        report += [
            "",
            "## 数据质量说明",
            "",
            "- `划走率` / `文案展开率` / `平均浏览图片数` 三项全为 `-`："
            "创作者中心对这几条作品没暴露该列（可能因为形态或数据量不足）。",
            "- 因此本项目的复盘**拿不到划走率**——这是抖音最直接的内容质量信号，"
            "缺它会让 HP（钩子）维度的验证变弱。后续发布前建议确认作品形态是否影响该指标可见性。",
            "",
            "## 全文案（创作者中心列表返回）",
            "",
            "```",
            title,
            "```",
        ]
        with open(os.path.join(vdir, "report.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(report) + "\n")

        sc = SCORES[i]
        composite = round(sum(sc[k] for k in
                              ("ER", "HP", "QL", "NA", "AB", "SR", "SAT")) / 7 * 2, 2)
        pred = [
            f"# {short} — 预测（Reconstructed）",
            "",
            "> ⚠️ **Reconstructed retrospective — NOT a blind prediction**",
            ">",
            "> 本条是在**已经看到实绩数据之后**反向打分的，目的是给 cheat-seed 提供"
            "「这个号过去做过什么、什么有效」的 context。",
            "> **不计入 `calibration_samples`** —— 校准只能来自发布前锁定的盲预测。",
            "",
            "## 元数据",
            "",
            f"- video id: `{vid}`",
            f"- 快照日: {SNAPSHOT}（真实发布日未取到）",
            "- 形态: 主锁系列（第 1 篇真实预测前无法确认真实形态）",
            f"- 数据: [videos/{stem}/report.md](../videos/{stem}/report.md)",
            "",
            "## 预测（Reconstructed — 事后反推）",
            "",
            "| 维度 | 分 |",
            "|---|---:|",
        ]
        for k in ("ER", "HP", "QL", "NA", "AB", "SR", "SAT"):
            pred.append(f"| {k} | {sc[k]} |")
        pred += [
            f"| **composite** | **{composite}** |",
            "",
            f"评分理由：{sc['why']}",
            "",
            "## 复盘",
            "",
            "| 指标 | 实测 |",
            "|---|---|",
        ]
        for k, v in raw.items():
            pred.append(f"| {k} | {v} |")
        pred += [
            "",
            f"**composite {composite}**  vs  **播放 {raw.get('播放')}** / "
            f"**收藏 {raw.get('收藏')}** / **吸粉 {raw.get('吸粉量')}**",
            "",
            "→ 与其他 3 条合并看：**composite 与播放的排序几乎无关，"
            "但与收藏 / 吸粉的排序高度一致**。详见 [rubric-memo.md](../rubric-memo.md)。",
        ]
        with open(os.path.join(PREDS, stem + ".md"), "w", encoding="utf-8") as f:
            f.write("\n".join(pred) + "\n")

        made.append((stem, composite, raw))
        print(f"✅ {stem}   composite={composite}  播放={raw.get('播放')} "
              f"收藏={raw.get('收藏')} 吸粉={raw.get('吸粉量')}")

    # ── 把"v0 预测的是播放，但这个号的播放不区分质量"这条观察写进 memo
    obs = [
        "",
        "---",
        "",
        "## OBS-001｜v0 的 composite 预测的是互动质量，不是播放（2026-10-09，N=4）",
        "",
        "**来源**：本项目 4 条历史作品（主锁系列）全部按 7 维反向打分后与实绩对照。",
        "**本段含实绩数字，故写在 memo 而非 rubric_notes** —— rubric_notes 是 blind 打分",
        "sub-agent 的白名单文件，不能含实绩。",
        "",
        "**观察**：",
        "",
        "| 排序依据 | 顺序（低→高） |",
        "|---|---|",
        "| 播放 | 选型 → 锁门 → 型or形 → 清洗保养 |",
        "| composite | 清洗保养 → 锁门 → 选型 → 型or形 |",
        "| 收藏 | 清洗保养 → 选型 → 锁门 → 型or形 |",
        "| 吸粉 | 清洗保养 → 选型 → 锁门 → 型or形 |",
        "",
        "**结论**：",
        "",
        "1. **播放几乎不区分内容质量**——4 条全部落在 1314–1783 这个窄带里（极差 1.36×）。"
        "这是新号被平台初始流量池限定的典型形态。",
        "2. **composite 与播放产生负相关**（Spearman ≈ −0.4，N=4 无统计意义，"
        "但方向错误本身就是信号）。",
        "3. **composite 与收藏 / 吸粉高度一致**（Spearman ≈ +0.8）。"
        "也就是说 v0 的维度在测「内容留得下多少人」，而不是「平台推给多少人」。",
        "",
        "**对下一次 bump 的含义**：",
        "",
        "- 若继续用 composite 预测**播放**，在 N≥5 之前会持续失准——因为因变量的方差"
        "主要来自平台分配，不是内容。",
        "- 候选方案 A：把预测对象从播放改成**收藏率 / 吸粉量**（可预测性高得多）。",
        "- 候选方案 B：保留播放预测，但 bucket 收窄（按本号 baseline 1594 的 ±20% 划），"
        "并明确声明「播放预测近乎常数，信息量低」。",
        "- 两个方案都要等 N≥5 才能正式走 bump 流程。**现在不要改公式。**",
        "",
    ]
    with open(MEMO, "a", encoding="utf-8") as f:
        f.write("\n".join(obs))
    print(f"\n📝 已把 OBS-001 追加到 {MEMO}")
    print(f"✅ 导入完成：{len(made)} 条 → videos/ + predictions/")


if __name__ == "__main__":
    main()
