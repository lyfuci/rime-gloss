# rime-gloss

Rime 通用学习扩展包：用任何语言打字时，在候选词旁边显示另一种语言的短释义和词性。要显示哪些目标语言可以配置；上屏内容不变。

```text
中文输入，目标 英/日        英文输入，目标 中
学习  v. study/learn        study   v. 学习
学校  n. school             school  n. 学校
```

这是东风破 [plum](https://github.com/rime/plum) 配方，小狼毫、鼠须管、fcitx5、ibus 都能装，不绑定任何一个前端。前端只负责显示 Rime 候选的注释。

## 安装

```bash
git clone --depth 1 https://github.com/rime/plum.git
cd plum
bash rime-install lyfuci/rime-gloss
```

然后在前端里「重新部署」。fcitx5 没被自动识别时：

```bash
rime_dir="$HOME/.local/share/fcitx5/rime" bash rime-install lyfuci/rime-gloss
```

详细说明见 [docs/install.md](docs/install.md)。

## 接到你正在用的方案

默认配方不会改你的方案配置。装完后，用脚本给任意方案加上释义：

```bash
# 中文拼音（雾凇），显示英语和日语
python3 tools/enable_schema.py --schema rime_ice --source zh --targets en,ja
# 英文输入方案，显示中文
python3 tools/enable_schema.py --schema melt_eng --source en --targets zh
```

```powershell
powershell -ExecutionPolicy Bypass -File tools\enable.ps1 -Schema rime_ice -Source zh -Targets en,ja
```

`--source` 是这个方案候选的语言，`--targets` 是想看的释义语言。也可以手动把 [patches/append.yaml](patches/append.yaml) 的几行贴进 `<方案>.custom.yaml` 的 `patch:` 下面。重新部署后，方案菜单里会多一个开关：`释义关 / 英 / 日 / 全部`（只有一种目标语言时没有「全部」）。

只想先看效果：部署后勾选「明月拼音·释义」（`rime_gloss_luna`），它用 Rime 自带的明月拼音。已装雾凇、想要独立的「雾凇拼音·释义」方案：

```bash
bash rime-install lyfuci/rime-gloss:recipes/ice
```

缺 `rime_ice.schema.yaml` 时不要装这个配方，部署会报错。

## 词表从哪来

每个语言对一组文件，`<输入语言>-<目标语言>`，例如 `zh-en`、`en-zh`、`ja-en`：

| 文件 | 内容 | 优先级 |
| --- | --- | --- |
| `gloss/user_<对>.tsv` | 你自己加的词，配方更新不会覆盖 | 最高 |
| `gloss/<对>.tsv` | 本仓库手写的种子词表 | 中 |
| `gloss/dict/<对>.tsv` | 从开源词典导入的大词表 | 最低 |

大词表不读进内存，而是按字节排好序、查词时在文件里二分查找，所以几十万条也不拖慢输入法。格式见 [docs/format.md](docs/format.md)：

```text
词<TAB>短释义<TAB>词性
运行<TAB>run<TAB>v.
```

现在只有中文到英语、日语的约 290 个种子词。导入开源词典（CC-CEDICT、JMdict、ECDICT）在做。

只做精确匹配：`学习` 有注释，不代表 `学习英语` 也有。例句、读音、整句翻译、联网词典不在范围内，它们不该塞进候选栏。

## 配方

| 命令后缀 | 内容 |
| --- | --- |
| `lyfuci/rime-gloss` | 词表 + Lua 滤镜 + 明月试用方案 |
| `:recipes/dicts_only` | 只更新词表 |
| `:recipes/ice` | 上面的全部，再加雾凇试用方案 |

## 开发

```bash
python3 tools/validate_tsv.py        # 词表格式、大词表排序
lua5.4 tests/filter_test.lua         # 滤镜（模拟 Rime 环境）
python3 tests/enable_schema_test.py  # 接入脚本
```

## 许可

代码、脚本和种子词表使用 [MIT](LICENSE)。从第三方词典导入的数据保留各自的许可证，放在单独的目录并注明出处，不按 MIT 再分发。
