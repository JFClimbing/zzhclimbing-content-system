#!/usr/bin/env python3
"""consolidated retro 执行器 —— 锁 → 追加复盘 → 校验锁

顺序是有意的：先锁预测段（写指纹），再追加复盘，最后校验。
如果追加时误改了预测段，verify 会报 MISMATCH —— 这就是 immutability 的实战检验。

用法:
  python tools/run_retro.py
"""
import json
import os
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PREDS = os.path.join(ROOT, "predictions")
LOCK = os.path.join(ROOT, ".cheat-hooks", "prediction_lock.py")
MEMO = os.path.join(ROOT, "rubric-memo.md")

# 每条作品的评论分析（数据来自 data/my_video_comments.json 实测）
RETRO = {
    "85c63f952d8c": """
### 评论分析（T+N，抓于 2026-10-09）

抓到 9 个评论 DOM 节点（含作者/按钮噪声），真实用户评论 3 条：

| 评论 | 作者 | 地域 | 时间 |
|---|---|---|---|
| 装备也需要保养 | BlueWool | 湖北 | 16 小时前 |
| 收一个磨损的报废的 | 世界霸主之蛇王 | 广东 | 17 小时前 |
| （无文字） | 腐竹 | 湖北 | 18 小时前 |

**两类信号**：
1. **认同类**（"装备也需要保养"）——观众把内容内化成了自己的判断，说明 ER 生效。
2. **交易类**（"收一个磨损的报废的"）——**有人在问能不能收报废主锁**。这是需求信号，
   但也是一个**责任敞口**：报废承重装备的流转涉及安全问题。回复策略要先想清楚。

**注意：本条的文案自己标注了「部分素材来源于 Hard is easy 装备之主锁篇（4）」** ——
即搬运/翻译内容。这在评论区没有引发负面反馈，但原创性是账号长期风险，需要单独立项讨论。

**地域分布**：湖北 / 广东 / 湖北 —— 无广西本地评论，说明流量来自推荐池而非本地社媒。
""",
    "04259132cb02": """
### 评论分析（T+N，抓于 2026-10-09）

抓到 7 个节点，真实用户评论 1 条 + 作者回复 1 条：

| 评论 | 作者 | 地域 | 时间 |
|---|---|---|---|
| [出去玩][出去玩][出去玩] | 腐竹 | 湖北 | 3 天前 |
| （作者回复） | Neverest 不止攀岩 | 广西 | 2 天前 |

**信号**：只有表情包评论，**没有一条关于主锁选型的实质讨论**。

这一条是 4 条里**播放最低（1314）**、评论也几乎没有的。它的 composite 是 7.43（第二高）
—— 说明**"选型"这个主题在评论区是冷的**：观众看完了，但没有话想说。

对比「型or形」（同样讲选型，但拿了 13 评论）：差别可能在于**"型or形"给了争议性的记忆点**
（D/H/O 型的字形梗），而"你真的会选吗"只是一个提问。
""",
    "28daac18c22e": """
### 评论分析（T+N，抓于 2026-10-09）

抓到 3 个节点，真实用户评论 1 条：

| 评论 | 作者 | 地域 | 时间 |
|---|---|---|---|
| 清晰明了 | BlueWool | 湖北 | 4 天前 |

**信号**：**"清晰明了"是教学质量认可，不是传播信号**。

这条的收藏量在 4 条里排第 3（9），播放 1470（中位）。评论只有 1 条说明：
**讲得清楚 ≠ 有人想说话**。工具型内容天然低评论——观众"收下就走"。

**这条支持 rubric 的一个方向**：对教程类内容，评论数不是一个好的质量指标，
**收藏率**才是。本条的收藏/播放 = 9/1470 = 0.61%，
而"型or形"是 16/1718 = 0.93%。

**作者反馈**：BlueWool 在 4 条里出现了 2 次（本条 + 清洗保养），
是**目前唯一的核心粉丝**。湖北，非本地。
""",
    "aa9e4cdcff80": """
### 评论分析（T+N，抓于 2026-10-09）

抓到 39 个节点（远超另外三条），真实用户评论含：

| 评论 | 作者 | 地域 | 时间 | 意义 |
|---|---|---|---|---|
| **现在关注以后就是老粉了** | 野生岛民阿聪 | 海南 | 14 小时前 | ⭐ **长期关注意向** |
| 小铭老师讲的真好，爱了爱了 | 稻城多吉 | 黑龙江 | 3 天前 | ⭐ **"老师"=权威认可 + 情感认同** |
| H型锁就是hms锁吗 | 不知道叫啥 | 云南 | 1 周前 | ⭐ **求知延伸提问** |
| （作者回复） | Neverest 不止攀岩 | 广西 | 7 小时前 | 作者在回复 |

**三个信号，逐个说**：

1. **「现在关注以后就是老粉了」= 直接解释了 32 吸粉量。**
   这是"我要长期跟这个号"的显式表达。4 条里只有这一条触发了它。

2. **「小铭老师讲的真好」——观众自发把作者升格为"老师"。**
   这是 SAT（教学人格）+ ER（认知突破）联合生效的证据。
   注意"爱了爱了"是情感表达，说明这条不只是"有用"，还**讨人喜欢**。

3. **「H型锁就是hms锁吗」——提问型评论，内容激发了求知欲。**
   但这是一条**未被满足的提问**：观众想知道"H型"和"HMS"是不是同一个东西。
   → **直接可用的下一条选题**，而且是评论区自己送上门的需求。

**地域分布**：海南 / 黑龙江 / 云南 / 广西 —— 跨度极大，全是推荐流量。
说明这个号目前**没有地域粉丝基础**，内容是被算法推给全国攀岩兴趣人群的。

**这一条是 4 条里唯一的"高表现样本"**：评论 13、分享 14、收藏 16、吸粉 32 全部第一，
但**播放 1718 只排第二**。这就是 OBS-001 的核心证据。
""",
}


def stem_to_key(stem):
    for k in RETRO:
        if k in stem:
            return k
    return None


def main():
    files = sorted(f for f in os.listdir(PREDS) if f.endswith(".md"))
    if not files:
        print("predictions/ 下没有文件")
        sys.exit(1)

    print("① 锁定预测段（写指纹）")
    r = subprocess.run([sys.executable, LOCK, "lock"] +
                       [os.path.join(PREDS, f) for f in files],
                       capture_output=True, text=True, encoding="utf-8")
    print(r.stdout.strip() or r.stderr.strip())

    print("\n② 追加复盘（评论分析）")
    for f in files:
        key = stem_to_key(f)
        if key is None:
            print(f"   - {f}：无对应评论数据，跳过")
            continue
        path = os.path.join(PREDS, f)
        text = open(path, encoding="utf-8").read()
        if "### 评论分析" in text:
            print(f"   - {f}：已有评论分析，跳过")
            continue
        block = RETRO[key].rstrip() + "\n"
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(block)
        print(f"   ✅ {f}")

    print("\n③ 校验锁（预测段是否被误改）")
    r = subprocess.run([sys.executable, LOCK, "verify"] +
                       [os.path.join(PREDS, f) for f in files],
                       capture_output=True, text=True, encoding="utf-8")
    print(r.stdout.strip() or r.stderr.strip())
    ok = r.returncode == 0

    print("\n④ 追加跨样本观察到 rubric-memo.md")
    text = open(MEMO, encoding="utf-8").read()
    if "OBS-002" not in text:
        with open(MEMO, "a", encoding="utf-8") as fh:
            fh.write("""
---

## OBS-002｜评论数不是教程类内容的质量指标；「关注意向」才是（2026-10-09，N=4）

**来源**：本项目 4 条作品全部抓取评论区后对照。

**观察**：

| 作品 | 评论数 | 收藏 | 吸粉 | 代表性评论 |
|---|---:|---:|---:|---|
| 型or形 | 13 | 16 | **32** | 「现在关注以后就是老粉了」 |
| 清洗保养 | 3 | 2 | 6 | 「装备也需要保养」 |
| 选型 | 2 | 7 | 7 | （只有表情包） |
| 锁门类型 | 1 | 9 | 9 | 「清晰明了」 |

**结论**：

1. **「清晰明了」型评论（质量认可）与传播无关。** 锁门类型那条被夸"清晰明了"，
   但评论 1 条、吸粉 9 —— 讲得清楚只说明没讲错，不说明有人想跟。
2. **唯一的高表现信号是「关注意向」评论**（"现在关注以后就是老粉了"）。
   这类评论出现时，吸粉量是其他条的 3.5–5 倍（32 vs 6/7/9）。
3. **提问型评论（"H型锁就是hms锁吗"）是选题矿**，不是质量指标。
   它说明内容激发了求知欲但没满足完 —— 应该变成下一条选题，而不是拿来打分。
4. **评论区地域分布与播放无关**（湖北/广东/海南/黑龙江/云南 / 广西本地为 0）——
   当前流量 100% 来自全国推荐池，没有本地粉丝基础。

**对 rubric 的含义**：

- 现有 7 维里没有"关注意向"这个维度。**候选新维度：`FI`（Follow Intent，关注意向）** ——
  内容是否让观众产生"我要长期跟这个号"的判断。它可能与 `AB`（受众广度）正相关，
  但机制不同：AB 是"多少人有这个问题"，FI 是"看完之后想不想继续看这个人"。
- 但这只有 1 个正样本，**N=1 不足以立维度**。等积累 3+ 条有「关注意向」评论的样本再议。
""")
        print("   ✅ OBS-002 已写入 rubric-memo.md")
    else:
        print("   - OBS-002 已存在，跳过")

    print(f"\n{'✅ 复盘完成，锁校验通过' if ok else '❌ 锁校验失败 —— 预测段被改动，需回滚'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
