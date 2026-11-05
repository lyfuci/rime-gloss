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

需要带 librime-lua 的 Rime（小狼毫 0.15+、鼠须管 1.0+，或装了 Lua 插件的 fcitx5/ibus）。Windows 从零开始的步骤和其他细节见 [docs/install.md](docs/install.md)。

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
bash rime-install lyfuci/rime-gloss:ice
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

种子词表是中文到英语、日语的约 290 个常用词。大词表从开源词典导入，按需安装：

| 配方 | 语言对 | 来源 | 条目 | 许可证 |
| --- | --- | --- | --- | --- |
| `:dict-zh-en` | 中文 → 英语 | CC-CEDICT | 约 20 万 | CC BY-SA 4.0 |
| `:dict-ja-en` | 日语 → 英语 | JMdict | 约 47 万 | CC BY-SA 4.0（EDRDG） |
| `:dict-en-zh` | 英语 → 中文 | ECDICT（常用 5 万词 + 考试词表） | 约 6 万 | MIT |
| `:dict-zh-ja` | 中文 → 日语 | 由 CC-CEDICT + JMdict 推导（见下） | 约 4 万词（简繁共 6.5 万键） | CC BY-SA 4.0 |
| `:dicts` | 以上全部 | | | |

```bash
bash rime-install lyfuci/rime-gloss lyfuci/rime-gloss:dict-zh-en
```

中文 → 日语没有现成的开源词典，`dict-zh-ja` 是推导出来的，规则在 [tools/cognates.py](tools/cognates.py)：

- **同形词**：中文词的繁体经 OpenCC 转成日文新字体（學習 → 学習），在 JMdict 里存在，并且两本词典的英文释义在主要义项上重合。`手纸`（卫生纸）和 `手紙`（信）这类不重合的会被排除。地名、人名只走这一条（北京 → 北京 ペキン）。
- **英文对译**：中文词的第一个释义和某个日语常用词（JMdict 的基础词汇 `ichi1`）的第一个释义完全相同，比如 "to eat" → 食べる。敬语、谦语、古语、罕用词不参与。
- 两者都有时，同形词至少要和对译词一样常用才优先。`爱人`、`工作`、`先生` 这类出了名的「同形异义词」只走英文对译。

按 Rime 语料词频算，最常用的 1000 / 5000 / 20000 个词分别覆盖约 93% / 85% / 69%；没覆盖的多是语气词和网络用语（呢、啊、楼主），日语里本来就没有直接对应。推导结果会有不地道的地方，例如给出的是近义词而不是最常用的说法。最常用的约 290 个词以手写种子词表为准，种子表优先于大词表。发现明显错误的词，可以写进 `gloss/user_zh-ja.tsv` 覆盖，或者提 issue。

### 更新词典、换成自己的来源

输入法本身不联网。词典有两种更新方式：

- **跟着仓库更新**：仓库每周从上游重新生成一次词典。重新运行上面的 `rime-install` 命令，再重新部署。
- **自己生成**：克隆本仓库后运行 `tools/build_dicts.py`，直接写进 Rime 用户目录：

  ```bash
  python3 tools/build_dicts.py --rime-dir "$APPDATA/Rime"             # 全部，最新上游
  python3 tools/build_dicts.py --rime-dir "$APPDATA/Rime" --only zh-en
  python3 tools/build_dicts.py --rime-dir "$APPDATA/Rime" --url cc-cedict=https://example.org/cedict.txt.gz
  python3 tools/build_dicts.py --rime-dir "$APPDATA/Rime" --config my-dicts.toml
  ```

  来源、格式和 URL 写在 [dicts.toml](dicts.toml)。复制一份改成自己的，可以换镜像、用本地文件，或加新的语言对；格式支持 `cedict`、`jmdict`、`ecdict` 和通用的 `tsv`（`词<TAB>释义<TAB>词性`）。生成后重新部署。

日语输入可以配 [rime-jaroomaji](https://github.com/lazyfoxchan/rime-jaroomaji)，步骤见 [docs/install.md](docs/install.md#日语输入)；片假名候选会按平假名再查一次。

只做精确匹配：`学习` 有注释，不代表 `学习英语` 也有。例句、读音、整句翻译、联网词典不在范围内，它们不该塞进候选栏。

## 配方

| 命令后缀 | 内容 |
| --- | --- |
| `lyfuci/rime-gloss` | 词表 + Lua 滤镜 + 明月试用方案 |
| `:dicts_only` | 只更新种子词表 |
| `:ice` | 上面的全部，再加雾凇试用方案 |
| `:dict-<语言对>`、`:dicts` | 导入的大词表，见上文 |

## 开发

```bash
python3 tools/validate_tsv.py        # 词表格式、大词表排序
lua5.4 tests/filter_test.lua         # 滤镜（模拟 Rime 环境）
python3 tests/enable_schema_test.py  # 接入脚本
python3 tests/build_dicts_test.py    # 词典转换（离线样例）
lua5.4 tests/dict_lookup_test.lua    # 在真实大词表上二分查找
```

## 许可

代码、脚本和种子词表使用 [MIT](LICENSE)。`gloss/dict/` 下导入的词典不属于 MIT，各自保留来源的许可证，出处、版本和许可证见 [gloss/dict/SOURCES.md](gloss/dict/SOURCES.md)。CC BY-SA 的词典再分发或修改后仍须按 CC BY-SA 共享。
