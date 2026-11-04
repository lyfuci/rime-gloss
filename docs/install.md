# 安装

适用：小狼毫 Weasel、鼠须管 Squirrel、fcitx5-rime、ibus-rime。包本身不绑定小狼毫。

## 东风破 plum（推荐）

先装 git、bash。Windows 可用 Git Bash。

```bash
git clone --depth 1 https://github.com/rime/plum.git
cd plum
bash rime-install lyfuci/rime-gloss
```

fcitx5 若没被自动识别：

```bash
rime_dir="$HOME/.local/share/fcitx5/rime" bash rime-install lyfuci/rime-gloss
```

只更新词表、不装脚本：

```bash
bash rime-install lyfuci/rime-gloss:recipes/dicts_only
```

已经装了雾凇、想多一个「雾凇拼音·释义」方案：

```bash
bash rime-install lyfuci/rime-gloss:recipes/ice
```

装完在前端里「重新部署」。

## 接到你正在用的方案

这是学习输入时最有用的接法：继续用雾凇 / 明月 / 双拼，只多一行注释。

1. 打开用户目录：
   - 小狼毫：`%APPDATA%\Rime`
   - 鼠须管：`~/Library/Rime`
   - fcitx5：`~/.local/share/fcitx5/rime`
2. 编辑 `<方案>.custom.yaml`，例如 `rime_ice.custom.yaml`。没有就新建，内容以 `patch:` 开头。
3. 在 `patch:` 下面加入 `patches/append.yaml` 里的四行，按你的方案改 `source`（候选的语言）和 `targets`（想看的语言）。
4. 重新部署。
5. 方案选单里应出现 `释义关 / 英 / 日 / 全部`。默认是第一种目标语言。

也可以在仓库里运行：

```bash
python3 tools/enable_schema.py --schema rime_ice --source zh --targets en,ja
# 英文输入方案看中文释义
python3 tools/enable_schema.py --schema melt_eng --source en --targets zh
```

Windows（PowerShell 脚本，需要手动运行；`Bypass` 只对这一次运行放开脚本限制）：

```powershell
powershell -ExecutionPolicy Bypass -File tools\enable.ps1 -Schema rime_ice -Source zh -Targets en,ja
```

脚本只在补丁文件里追加滤镜，不会改词库，也不会覆盖已有的 `rime_gloss_filter` 行。

## 零改配置试用

默认配方带 `rime_gloss_luna.schema.yaml`。部署后在方案列表加入「明月拼音·释义」即可试注释。它用的是 Rime 自带明月拼音，不是雾凇词库。

加入方案列表（`default.custom.yaml`）：

```yaml
patch:
  schema_list/@next:
    schema: rime_gloss_luna
```

或在小狼毫「输入法设定」里勾选。

## 更新

```bash
cd plum
bash rime-install lyfuci/rime-gloss
```

然后重新部署。`gloss/user_<输入语言>-<目标语言>.tsv`（如 `gloss/user_zh-en.tsv`）不在配方里，更新不会覆盖它们。
