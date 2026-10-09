# zzhclimbing-content-system

> 抖音「**Neverest 不止攀岩**」的内容预测与校准系统 —— 把"感觉"变成可校准预测。

**账号**：Neverest 不止攀岩 · 抖音号 `zzhclimbing` · 广西·桂林
**内容形态**：攀岩教程 / 装备分享（`tutorial-builder`）
**当前状态**：rubric v0（等权占位，未校准）· 校准样本 0 / 5 · baseline 播放 1,594

---

## 这是什么

一套 5 阶段闭环：**打分 → 盲预测 → 发布 → 复盘 → 进化 rubric**。

核心不是"AI 帮你写稿"，而是**逼你在看到数据之前写下判断**，然后用真实数据检验它。
前 5 篇的预测精度大约 ±50% —— 这是 cold-start 的数学事实。**前 5 篇你不是在做决策，你是在收集数据。**

三条不可妥协的原则：

1. **盲预测** —— 预测必须在看到任何实际数据**之前**写完，写完即不可改。本仓库用
   `.cheat-hooks/prediction_lock.py`（SHA-256 指纹账本）强制执行。
2. **升级 = 全量重打** —— rubric 升级时，校准池所有样本必须用新公式重打分。
3. **rubric 是工作台，不是博物馆** —— 被推翻的观察删掉，git history 才是档案。

---

## 快速开始（任何平台）

### 1. 依赖

```bash
python -m pip install -r requirements.txt
```

只依赖 **Playwright**。**不需要** `playwright install` 下载 Chromium ——
脚本用系统已装的浏览器：Windows 默认 Edge，macOS / Linux 默认 Chrome。

要指定别的浏览器：

```bash
# Windows
set DSH_BROWSER_CHANNEL=chrome
# macOS / Linux
export DSH_BROWSER_CHANNEL=chromium
```

### 2. 首次登录（每账号一次）

```bash
python tools/dy_review.py
```

会弹出一个可见浏览器窗口，扫码登录抖音创作者中心。**登录态持久化到 `.auth-edge/`**
（已 gitignore —— 里面是 sessionid，等同账号密码，绝不提交）。

> ⚠️ **一个账号一个 `.auth-edge/`**。同一台机器上跑多个抖音号时，各自 clone 一份到
> 不同目录，否则登录态会互相顶掉。

### 3. 常用命令

```bash
# 抓自己作品的后台数据（播放/点赞/评论/分享/收藏/吸粉）
python tools/dy_review.py
python tools/dy_review.py --table        # 只打表格
python tools/dy_review.py --diff         # 只看与上次快照的增量

# 抓自己作品的视频 ID + top 评论（复盘的前提）
python tools/dy_my_comments.py --limit 4

# 对标账号：关注列表 → 画像 → 作品 → 单条数据
python tools/dy_following.py
python tools/dy_characterize.py
python tools/dy_benchmark_works.py --top 6
python tools/dy_sample_metrics.py --account 梦幻拍档 --limit 6

# 复盘：锁预测段 → 追加复盘 → 校验锁没被破
python tools/run_retro.py

# 预测锁（单独用）
python .cheat-hooks/prediction_lock.py lock   predictions/xxx.md
python .cheat-hooks/prediction_lock.py verify predictions/xxx.md
python .cheat-hooks/prediction_lock.py verify-all
python .cheat-hooks/prediction_lock.py selftest   # 自检
```

---

## 目录结构

```
.
├── .cheat-state.json          状态文件 —— 所有子流程共享的上下文
├── rubric_notes.md            ⭐ 怎么打分（维度定义 / 公式 / bucket 边界）
├── rubric-memo.md             ⭐ 观察记录（含实绩证据 —— 打分 sub-agent 硬禁读）
├── script_patterns.md         怎么写（与 rubric 解耦）
├── benchmark.md               对标账号 reference
├── audience.md                受众画像骨架
├── WORKFLOW.md / STATUS.md    流程文档 / 看板
├── scripts/                   拍前草稿
├── predictions/               ⭐ 不可变预测日志（指纹锁保护）
├── videos/<date>_<id>_<短名>/ 拍后工作区：report.md + script.md
├── samples/<账号名>/<video-id>/  对标样本：meta.md + transcript.md
├── data/                      抓取快照（JSON）
├── tools/                     抓取与执行脚本
└── .cheat-hooks/              prediction_lock.py（其余为 Claude Code hook 副本，已忽略）
```

**关键区分**：`rubric_notes.md` 只能含**通用语言**（公式、维度定义、bucket 边界），
因为它是 blind 打分 sub-agent 的白名单文件。任何含**真实视频名 / 实绩数字**的观察
必须写进 `rubric-memo.md`。这条隔离被破坏，盲预测就失效了。

---

## 跨平台说明

| 项 | 处理 |
|---|---|
| 浏览器 | `tools/*.py` 全部走统一的 `launch()`，平台自动探测；`DSH_BROWSER_CHANNEL` 可覆盖 |
| 路径 | 全部用 `os.path.dirname(__file__)` 相对定位，无绝对路径 |
| 控制台编码 | 所有脚本开头 `sys.stdout.reconfigure(encoding="utf-8")`，中文 Windows 的 GBK 控制台不会炸 |
| 登录态 | `.auth-edge/` 项目内相对路径，每账号独立 |
| 已知限制 | 抖音网页版部分选择器（`data-e2e`）会随改版失效；脚本内已写明每个坑的实测结论 |

### ⚠️ 本机专属：`github.com:443` 不可达，走 SSH 443 跳板

这台机器上 `github.com` 的 TCP 443 **直接超时**（DNS 能解析，但连不上），
所以 `git push https://github.com/...` 必然失败。但 `ssh.github.com:443`、
`api.github.com`、`codeload.github.com` 都是通的。

解法是 `~/.ssh/config` 里把 github.com 透明改道 443：

```
Host github.com
  HostName ssh.github.com
  Port 443
  User git
  IdentityFile ~/.ssh/id_ed25519
  IdentitiesOnly yes
  StrictHostKeyChecking accept-new
  ServerAliveInterval 30
```

```bash
git remote set-url origin git@github.com:<owner>/<repo>.git
git push -u origin main
```

**三个必须注意的坑**（都踩过）：

1. **`~/.ssh/config` 和 `known_hosts` 必须是无 BOM 的 UTF-8。** PowerShell 5.1 的
   `-Encoding UTF8` / `Set-Content` 会写 BOM，ssh 解析会出错。用
   `[System.IO.File]::WriteAllText($p, $s, (New-Object System.Text.UTF8Encoding($false)))`。
2. **别用 `HostKeyAlias`。** 加了之后 known_hosts 查找会变成 `[ssh.github.com]:443`，
   反而触发 `Host key verification failed`。
3. **known_hosts 需要 `[github.com]:443` 这条记录。** 本机 `ssh-keyscan` 也被挡，
   所以做法是：把已有的 `[ssh.github.com]:443` 那几行**改个名**复制一份
   （同一台服务器，密钥相同）。

另外 git 可能用它自己捆绑的 ssh（不读系统 known_hosts）。固定用系统的：

```bash
git config --global core.sshCommand "C:/Windows/System32/OpenSSH/ssh.exe -o BatchMode=yes -o ConnectTimeout=20"
```

（macOS / Linux 上不需要这一整节 —— 直接用 HTTPS 即可。）

### 踩过的坑（都写在对应脚本的 docstring 里）

- `?showTab=following` **不触发**关注列表渲染 —— SPA 只在点击时挂载
- 关注列表卡片类名带哈希后缀且会变 —— 用 `sec_uid` 前缀 `MS4wLjAB` 精确匹配
- 个人页作品列表的 `/video/` 链接会被**推荐位污染** —— 逐条进视频页核对作者
- 视频页 `data-e2e="video-like-count"` **已失效** —— 点赞数目前抓不到
- 登录成功后抖音跳**创作者中心首页**而非作品管理页 —— 检测到已登录要重新导航

---

## 数据字典（`data/`）

| 文件 | 内容 |
|---|---|
| `dy_works_<日期>.json` | 自己作品的创作者中心快照（播放/赞/评/享/藏/划走/吸粉） |
| `my_video_comments.json` | 自己作品的视频 ID + 评论 |
| `douyin_self.json` | 本号资料（抖音号/简介/关注/粉丝/获赞） |
| `douyin_following.json` | 关注列表 |
| `douyin_benchmark_pool.json` | 关注账号画像 |
| `douyin_benchmark_works.json` | 对标候选作品列表 |
| `benchmark_sample_metrics.json` | 对标样本单条数据 |

---

## 现在该做什么

当前 **校准样本 0 / 5**。要脱离 cold-start，需要 5 次完整闭环：

1. 写一篇稿子 → `scripts/`
2. 打分（不写文件）
3. **发布前**写盲预测 → `predictions/`（写完锁死）
4. 发布 → 登记
5. T+3（视频）/ T+7~T+30（图文）→ 抓数据 + 复盘

**已有的 4 条主锁作品是 `reconstructed` 预测（事后反推），不计入校准样本。**
它们只提供选题 context 和 baseline。真正的校准从**下一篇盲预测**开始。

---

## 参考

- `benchmark.md` —— 对标账号 **梦幻拍档**（户外装备党 · 4.0万粉）
- `rubric-memo.md` —— OBS-001 / OBS-002 两条跨样本观察
