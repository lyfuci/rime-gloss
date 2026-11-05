# rime-gloss

Rime 通用学习扩展包：用任何语言打字时，在候选词旁边显示另一种语言的短释义和词性。要显示哪些目标语言可以配置；上屏内容不变。

```text
中文输入，目标 英/日        英文输入，目标 中
学习  v. study/learn        study   v. 学习
学校  n. school             school  n. 学校
```

这是东风破 [plum](https://github.com/rime/plum) 配方，小狼毫、鼠须管、fcitx5、ibus 都能装，不绑定任何一个前端。前端只负责显示 Rime 候选的注释。

## 安装

> 让 AI 代理替你安装：把本仓库链接发给它，让它按下文「[给 AI 代理的安装流程](#给-ai-代理的安装流程)」执行。

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

## 自己改词，再分享出去

释义不对、缺词，或者想隐藏某个词的释义，都写在 Rime 用户目录的 `gloss/user_<语言对>.tsv` 里（例如 `%APPDATA%\Rime\gloss\user_zh-ja.tsv`），重新部署后立即生效，更新配方也不会覆盖：

```text
西学	西洋の学問	名
戏谑	からかう	動
洗雪	-
```

最后一行的 `-` 表示「这个词不显示释义」，用来屏蔽大词表里的错误条目。

觉得改得对，可以分享给所有人：在本仓库的克隆里运行

```bash
python3 tools/contribute.py --rime-dir "$APPDATA/Rime"
```

脚本会列出你 `user_*.tsv` 里新增和改动的行，确认后把它们合并进仓库的种子词表 `gloss/<语言对>.tsv`，从最新的 main 开分支、提交并开 PR（需要 git 和登录过的 gh）。只上传这些行，别的什么都不传；输入法本身也不记录、不上传你打的字。合并后，所有人下次运行 `rime-install` 就能用上。`--dry-run` 只预览，`--no-pr` 只改本地克隆里的文件。

分享出去的词按 MIT 许可进入仓库，所以请只提交自己写的释义，不要整段抄别的词典。

## 配方

| 命令后缀 | 内容 |
| --- | --- |
| `lyfuci/rime-gloss` | 词表 + Lua 滤镜 + 明月试用方案 |
| `:dicts_only` | 只更新种子词表 |
| `:ice` | 上面的全部，再加雾凇试用方案 |
| `:dict-<语言对>`、`:dicts` | 导入的大词表，见上文 |

## 给 AI 代理的安装流程

这一节写给替用户安装的 AI 代理（Claude Code、Codex 等）：照顺序执行，每一步都有预期结果和检查方法。

**规则**

- 不覆盖用户已有的配置。`default.custom.yaml`、`<方案>.custom.yaml` 只做合并、追加；改之前先读一遍。
- 只往 Rime 用户目录写文件，不改前端的安装目录。
- 卸载、删除文件、改用户已有方案之前，先问用户。
- 每一步看到「预期」之外的输出就停下，对照文末「排错」处理。

### 1. 确认前端和用户目录

| 前端 | 用户目录 | 重新部署 | 最低版本 |
| --- | --- | --- | --- |
| 小狼毫（Windows） | `%APPDATA%\Rime` | `"C:\Program Files\Rime\weasel-<版本>\WeaselDeployer.exe" /deploy` | 0.15（自带 librime-lua） |
| 鼠须管（macOS） | `~/Library/Rime` | `"/Library/Input Methods/Squirrel.app/Contents/MacOS/Squirrel" --reload` | 1.0 |
| fcitx5-rime | `~/.local/share/fcitx5/rime` | 托盘菜单「重新部署」，或重启 fcitx5 | 需要 librime 的 Lua 插件 |
| ibus-rime | `~/.config/ibus/rime` | `ibus restart` | 需要 librime 的 Lua 插件 |

- 小狼毫的版本看安装目录名 `C:\Program Files\Rime\weasel-<版本>`。低于 0.15 先请用户升级。
- fcitx5 / ibus 先确认 Lua 插件已装：Debian/Ubuntu 是 `librime-plugin-lua`，Arch 是 `librime-lua`。
- 用户目录不存在：先让前端部署一次，它会生成目录。

### 2. 准备 plum

需要 git 和 bash。Windows 上用 Git Bash：从 WSL 可以调用 `"/mnt/c/Program Files/Git/bin/bash.exe" -lc '…'`，`$APPDATA` 在 Git Bash 里可用。

```bash
[ -d ~/plum ] || git clone --depth 1 https://github.com/rime/plum.git ~/plum
```

### 3. 安装

把 `<用户目录>` 换成第 1 步查到的路径。Windows 用 Git Bash 时写 `"$APPDATA/Rime"`。按需要选配方：

```bash
cd ~/plum
rime_dir="<用户目录>" bash rime-install lyfuci/rime-gloss lyfuci/rime-gloss:dict-zh-en lyfuci/rime-gloss:dict-zh-ja
# 还要日语输入：加装日语方案和日→英词典
rime_dir="<用户目录>" bash rime-install lazyfoxchan/rime-jaroomaji lyfuci/rime-gloss:dict-ja-en
# 英文输入看中文：
rime_dir="<用户目录>" bash rime-install lyfuci/rime-gloss:dict-en-zh
```

预期：每个配方输出 `Installing: …`，结尾是 `Updated ~ N files`；重复安装时是 `No files updated`。出现 `Invalid recipe` 或 `Error` 就停下。

检查：用户目录里应有 `lua/rime_gloss_filter.lua`、`gloss/zh-en.tsv`、`gloss/zh-ja.tsv`、`rime_gloss_luna.schema.yaml`，以及装了的 `gloss/dict/<语言对>.tsv`。

### 4. 接到方案上

先克隆本仓库，接入脚本在里面：

```bash
[ -d ~/rime-gloss ] || git clone --depth 1 https://github.com/lyfuci/rime-gloss.git ~/rime-gloss
```

**a. 给已有方案加释义（推荐）**：每个方案运行一次。`--source` 是这个方案候选的语言，`--targets` 是想看的释义语言：

| 方案 | schema id | 参数 |
| --- | --- | --- |
| 雾凇拼音 | `rime_ice` | `--source zh --targets en,ja` |
| 明月拼音 | `luna_pinyin` | `--source zh --targets en,ja` |
| 日语罗马字（jaroomaji） | `jaroomaji` | `--source ja --targets en` |
| 英文（melt_eng 等） | `melt_eng` | `--source en --targets zh` |

```bash
python3 ~/rime-gloss/tools/enable_schema.py --schema <schema id> --source <源> --targets <目标> --rime-dir "<用户目录>"
```

预期输出 `created: …`、`appended gloss patch: …` 或 `already enabled: …`。脚本只追加，不改已有内容；返回码 2 表示文件里没有顶层 `patch:`，这时不要改，问用户。没有 Python 的 Windows 用 `tools\enable.ps1 -Schema <id> -Source <源> -Targets <目标>`。

**b. 试用方案**：「明月拼音·释义」（`rime_gloss_luna`）不改任何已有方案，适合先看效果。

**c. 加进方案列表**：要用的方案（`rime_gloss_luna`、`jaroomaji` 等）必须在 `default.custom.yaml` 的 `schema_list` 里。合并，不要覆盖：

- 文件不存在或为空：写入

  ```yaml
  patch:
    schema_list:
      - schema: rime_gloss_luna
      - schema: luna_pinyin
  ```

- 文件已有 `patch:` 和 `schema_list:`：在列表里追加缺的 `- schema: <id>`，保留原有条目和顺序。
- 只有 `patch:` 没有 `schema_list:`：在 `patch:` 下加 `schema_list:`。注意这会替换前端的默认列表，所以把用户原来在用的方案（看 `build/default.yaml` 里的 `schema_list`）也写进去。

### 5. 重新部署

用第 1 步表里的命令。小狼毫的部署命令返回 0 即完成；首次编译大词库的方案（如 jaroomaji）可能要几十秒。

### 6. 验证

1. `build/<schema id>.schema.yaml` 存在，并且包含 `lua_filter@*rime_gloss_filter` 和 `gloss_` 开关。
2. `build/default.yaml` 的 `schema_list` 里有要用的方案。
3. 日志里没有 `invalid schema definition`、`error creating filter`。小狼毫的日志在 `%TEMP%\rime.weasel\`。
4. 请用户在该方案里打字。之后日志里应出现一行 `[rime-gloss] zh-en mem=… dict=yes`；`dict=no` 表示对应语言对的大词表没装。
5. 请用户确认候选旁有释义：
   - 中文方案打 `xuexi`，「学习」旁显示 `v. study/learn`。
   - jaroomaji 先按 Shift 切到「あ」（默认英数模式），再打 `taberu`，「食べる」旁显示 `v. to eat`。
   - 按 F4（或 `` Ctrl+` ``）打开方案菜单，能在 `释义关 / 英 / 日 / 全部` 之间切换。

### 排错

| 现象 | 原因与处理 |
| --- | --- |
| plum 报 `Invalid recipe` | 用了旧写法 `:recipes/xxx`，改成 `:dict-zh-en` 这类根目录配方名 |
| 方案列表里没有新方案 | 没加进 `schema_list`，或没重新部署 |
| 日志 `invalid schema definition` | 方案文件损坏或版本太旧，重新运行第 3 步 |
| 日志 `error creating filter: 'lua_filter'` | 前端没有 librime-lua：小狼毫低于 0.15，或 fcitx5/ibus 没装 Lua 插件 |
| 候选没有释义，日志里也没有 `[rime-gloss]` | 当前不是接了释义的方案，或方案菜单里选了「释义关」 |
| 只有部分词有释义 | 正常：只做整词精确匹配。装对应的 `:dict-<语言对>` 能覆盖更多词 |
| 明月拼音出繁体时「日」没有释义 | 种子词表是简体词条。在 `luna_pinyin.custom.yaml` 加 `switches/@2/reset: 1` 默认简体 |
| jaroomaji 打字只出英文字母 | 在英数模式，按 Shift 切到「あ」 |

### 更新与卸载

- 更新：重新运行第 3 步的命令，再重新部署。
- 卸载（先问用户）：删除用户目录里的 `lua/rime_gloss_filter.lua`、`gloss/`、`rime_gloss_*.schema.yaml`，从各 `<方案>.custom.yaml` 删掉 `rime_gloss_filter`、`gloss_`、`rime_gloss/` 那几行，再从 `schema_list` 去掉 `rime_gloss_luna`，重新部署。

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
