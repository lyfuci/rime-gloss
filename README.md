# rime-gloss

Rime 通用学习扩展包。打中文时，在候选词旁边显示英语 / 日语的词性和一句短解释。上屏内容不变。

不改小狼毫，也不做插件市场安装包。小狼毫没有插件市场。这个仓库是东风破 [plum](https://github.com/rime/plum) 配方，小狼毫、鼠须管、fcitx 都能装。

```text
你好    你好    intj. hello
        学习    v. study/learn · 動 学ぶ／勉強する
```

## 安装

仓库地址按你的 GitHub 账号 `lyfuci` 来写。若你改了仓库名，把命令里的用户名一并改掉。

```bash
git clone --depth 1 https://github.com/rime/plum.git
cd plum
bash rime-install lyfuci/rime-gloss
```

然后在小狼毫里「重新部署」。

fcitx5：

```bash
rime_dir="$HOME/.local/share/fcitx5/rime" bash rime-install lyfuci/rime-gloss
```

详细说明见 [docs/install.md](docs/install.md)。

## 接到雾凇或其他方案

默认配方不会改你的 `rime_ice.custom.yaml`，避免覆盖个人配置。装完后任选一种：

贴进 `rime_ice.custom.yaml` 的 `patch:` 下面（完整片段在 [patches/append.yaml](patches/append.yaml)）：

```yaml
patch:
  engine/filters/@next: lua_filter@rime_gloss_filter
  switches/@next: {options: [gloss_off, gloss_en, gloss_ja, gloss_both], states: [释义关, 英, 日, 双语], reset: 1}
  rime_gloss/default: en
```

或：

```bash
python3 tools/enable_schema.py --schema rime_ice
```

```powershell
powershell -ExecutionPolicy Bypass -File tools\enable.ps1 -Schema rime_ice
```

重新部署。方案菜单里会出现 `释义关 / 英 / 日 / 双语`，默认「英」。

只想先看效果、不想改现有方案：部署后勾选「明月拼音·释义」（`rime_gloss_luna`）。它用 Rime 自带的明月拼音。

已安装雾凇、想要独立方案「雾凇拼音·释义」：

```bash
bash rime-install lyfuci/rime-gloss:recipes/ice
```

缺 `rime_ice.schema.yaml` 时不要装这个配方，部署会报错。

## 现在能做什么

- 候选注释，不改变上屏
- 关 / 英 / 日 / 双语
- 精确匹配词条。`学习` 有注释，不代表 `学习英语` 也有
- 种子词表约 290 个常用词，用来打通链路
- 用户词放 `gloss/user_en.tsv`、`gloss/user_ja.tsv`，更新配方不会覆盖

还没有：例句、读音、SRS、整句翻译、网络词典。那些不该塞进输入法候选栏。

## 自己加词

格式见 [docs/format.md](docs/format.md)。

```text
中文<TAB>简释<TAB>词性
运行<TAB>run<TAB>v.
```

改的是用户目录里的 `gloss/en.tsv` 或 `gloss/user_en.tsv`，改完重新部署。

## 配方

| 命令后缀 | 内容 |
| --- | --- |
| `lyfuci/rime-gloss` | 词表 + Lua + 明月试用方案 |
| `:recipes/dicts_only` | 只更新词表 |
| `:recipes/ice` | 上面的全部，再加雾凇试用方案 |

## 许可

仓库代码、脚本和这份种子词表使用 [MIT](LICENSE)。

以后若导入 CC-CEDICT、JMdict 等词典，必须单独保留它们的许可证，不能当成 MIT 数据再分发。本仓库的种子词是短注释，不是这些词典的拷贝。

## 设计

词表和脚本与前端分开。小狼毫只负责显示 Rime 候选的 `comment`。换鼠须管或 fcitx 不用改数据。
