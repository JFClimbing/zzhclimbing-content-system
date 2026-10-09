#!/usr/bin/env python3
"""cheat-learn-from Phase 6/7 落盘 —— 跑完即删

写两个文件 + 更新 state：
  script_patterns.md  加「对标 梦幻拍档 借鉴」段（5 个 pattern）
  rubric_notes.md     加 "Benchmark-derived initial signals" 段（**纯定性，零实绩**）
  .cheat-state.json   benchmark_status: pending → imported
"""
import json
import os
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── 6c. script_patterns.md ──────────────────────────────────────────────
PATTERNS = """
---

## 对标 梦幻拍档 借鉴（imported on 2026-10-09，6 条样本）

> 这些 pattern 来自对标账号 —— **Imported, untested on my channel**。
> 实拍验证后（≥2 次跑出 + 复盘确认有效）再去掉这个标记，升入正式 pattern 库。
> 样本与实绩见 [benchmark.md](benchmark.md)；机器可读数据见 `data/benchmark_sample_metrics.json`。

### Pattern C1（对标）：标题 = 一个观众此刻正在纠结的具体决策点

**来自**: 样本 #2 / #3 / #5（三条全部）
**描述**: 标题不是知识点，是**一个具体决策**。三条都是问句，都用"隐含你做错了"或
"把选择困难写进标题"的手法：「…怎么**正确**修复？」（暗示多数人做错）、
「**一定要**有…**吗**？」（先立争议）、「…**纠结** A 还是 B？」（把纠结本身当标题）。
**原理**: 观众刷到时不需要"被吸引"，只需要**确认这条在说我现在正烦的那件事**。
**触发条件**: 装备选型 / 装备故障 / 使用误区类选题。

### Pattern C2（对标）：前 25 秒进入「判断层」，不做铺垫

**来自**: 样本 #3 / #5 的 AI 章节时间轴
**描述**: 没有自我介绍、没有"今天教大家"。第一条信息就是**判断**：
「修复前提 —— 什么情况才能修」（#3，00:24）、「干攀镐不能用于攀冰」（#5，00:01，**开局破误区**）。
**原理**: 抖音前 3 秒决定划走率，铺垫就是划走率。
**触发条件**: 所有教程类；尤其"有前提条件"的内容（先讲不能用的场景，再讲怎么用）。

### Pattern C3（对标）：双模态 —— 干货 2.5–5 分钟，体验 30 秒，不混

**来自**: 全部 6 条
**描述**: 干货轨 2:31 / 3:54 / 4:43；体验轨 0:30 / 0:31。**没有一个中间值。**
**原理**: 两种内容的最优时长由**消费方式**决定 —— 干货要被"存下来慢慢看"，
体验要被"30 秒爽完转走"。折中时长两头不讨好。
**触发条件**: 决定一条内容属于哪条轨之后，按对应时长做，不要折中。

### Pattern C4（对标）：用「我自己的选择」收尾，不用中立总结

**来自**: 样本 #5（02:54「个人选择与建议 —— 作者因攀冰多选择 quark」）
**描述**: 结尾给的是**作者自己的答案**，不是"综上所述"。
**原理**: 建立**教学人格**。中立总结是说明书的语气；给出自己的偏好是人的语气。
**触发条件**: 任何有"选型 / 取舍"的选题。注意：安全规范类内容不适用（不宜给"个人偏好"）。

### Pattern C5（对标）：装备修复用系列编号

**来自**: 样本 #3 标题带「第3集」
**描述**: 该号把装备修复做成**编号系列**。
**原理**: 系列化让单条内容自带"还有别的"预期，提高主页停留和关注转化。
**触发条件**: 同一品类能拆 3 条以上时。**你已经在用**（主锁系列）—— 保持。
"""

# ── 6d. rubric_notes.md（纯定性，零实绩）────────────────────────────────
SIGNALS = """
---

## Benchmark-derived initial signals

> 来自 [benchmark.md](benchmark.md) 的对标账号（N=6 样本，import on 2026-10-09）。
> **仅定性方向，不直接采纳为数值权重** —— 6 个样本拟合必然过拟合。
> 等你自己 N≥5 校准样本后正式 bump 时**再决定**是否调权重。
>
> **本段刻意不含任何真实视频名 / 实绩数字** —— rubric_notes.md 是 blind 打分
> sub-agent 的白名单文件，只能含通用语言。含证据的推导与数字在
> [benchmark.md](benchmark.md) 与 [rubric-memo.md](rubric-memo.md)。

- **看起来重要的维度**: `QL`（可复制内容密度）· `HP`（问题陈述清晰度）·
  `NA`（递进感 —— 但**只在长形态**里有效）
- **看起来不显著的维度**: `ER` · `SAT` · `SR` —— 高低样本在这三维上分布无明显差异，
  无法解释表现差异。可能是**及格线**而非**区分度**
- **一个形态层面的发现（重要）**: 该对标跑**双轨** —— 长干货与短体验，
  两轨的**主指标不同**（一轨靠收藏，一轨靠分享）。
  单一 composite 会把两轨样本混在一根轴上排序，产生**系统性误判**。
  → 候选方向：将来 bump 时按形态分别设 bucket，而不是全局一套边界
- **Claude 给的初始建议**: 对标是「**大众刚需决策点 + 高可执行密度 + 个人选择收尾**」型，
  不是「专业权威」型
- **一个便于迁移的推论**（对教程形态）：把「个人选择收尾」用来**对冲教程固有的说教感** ——
  结尾给出"我自己怎么选"，而不是"综上所述"
"""


def main():
    # script_patterns.md
    p = os.path.join(ROOT, "script_patterns.md")
    t = open(p, encoding="utf-8").read()
    if "对标 梦幻拍档 借鉴" in t:
        print("script_patterns.md: 已有该段，跳过")
    else:
        open(p, "a", encoding="utf-8").write(PATTERNS)
        print("✅ script_patterns.md: 已加「对标 梦幻拍档 借鉴」（5 个 pattern）")

    # rubric_notes.md
    p = os.path.join(ROOT, "rubric_notes.md")
    t = open(p, encoding="utf-8").read()
    if "Benchmark-derived initial signals" in t:
        print("rubric_notes.md: 已有该段，跳过")
    else:
        open(p, "a", encoding="utf-8").write(SIGNALS)
        print("✅ rubric_notes.md: 已加 benchmark signals（纯定性，零实绩）")

    # 白名单自检：rubric_notes.md 不得含实绩数字或样本名
    t = open(os.path.join(ROOT, "rubric_notes.md"), encoding="utf-8").read()
    bad = []
    for token in ["梦幻拍档", "46.7", "1,945", "1945", "冬季攀冰", "DWR", "dwr",
                  "nomic", "quark", "羽绒", "冰镐"]:
        if token in t:
            bad.append(token)
    print(f"\n🔒 blind 白名单自检: {'✅ 干净（无样本名 / 无实绩数字）' if not bad else '❌ 含泄漏: ' + ', '.join(bad)}")

    # state
    sp = os.path.join(ROOT, ".cheat-state.json")
    st = json.load(open(sp, encoding="utf-8"))
    st["benchmark_status"] = "imported"
    st["benchmark_name"] = "梦幻拍档"
    st["benchmark_sample_count"] = 6
    json.dump(st, open(sp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"✅ state: benchmark_status=imported, name=梦幻拍档, samples=6")


if __name__ == "__main__":
    main()
