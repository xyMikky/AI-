---
name: multilingual-lyrics-reader
description: 多语言歌曲学习点读 HTML 生成工具。将歌词（txt/lrc/qrc/QQ 音乐加密 _qm.qrc）切分为词汇级或短语级点读块，生成可本地打开的 HTML，并可结合 mp3/flac 按 LRC/QRC 时间轴切分逐句原唱音频；支持中文/粤语、日语、韩语、英语等语言的浏览器 TTS 朗读，可通过 --language/--speech-lang 指定发音语言。日语提供 SudachiPy 分词、假名、罗马音增强；QQ _qm.qrc 可提供词级原唱点击。适用于多语言歌曲学习、歌词词汇拆解、听写跟唱、逐句/逐词原唱点读页面制作。关键词：多语言歌词、粤语、韩语、英语、日语、点读 HTML、LRC、QRC、QQ 音乐歌词解密、原唱切片、TTS、分词。
---

# 多语言歌词点读 HTML 生成器

## 概述

这个 Skill 把多语言歌词和可选音频转换为本地点读学习页。输出是一个 HTML 文件，用户可双击打开，用于逐词/逐短语查看读音、罗马化/转写、中文释义，点击单词或句子听发音，并通过 CSV 反复校对词义。支持中文/粤语、日语、韩语、英语等语言；粤语会启用粤拼（Jyutping），日语会额外启用假名、罗马音和 SudachiPy 分词增强。

核心脚本位于 `scripts/build_reader.py`，辅助脚本包括：

- `scripts/qrc_decoder.py`：解密 QQ 音乐本地 `_qm.qrc`。
- `scripts/qq_des.py` / `scripts/qq_des_tables.py`：QQ 定制 DES。
- `scripts/audio_splitter.py`：用 ffmpeg 按时间轴切分原唱音频。
- `scripts/word_timing.py`：解析 QRC 词级时间轴。

完整使用说明见 `references/USAGE_GUIDE.md`。

## 使用场景

- 用户提供任意语言的 `.lrc + .mp3/.flac`，希望生成整首逐句原唱点读页。
- 用户提供粤语歌词，希望显示粤拼（Jyutping）并用粤语 TTS 朗读词汇或短语。
- 用户提供中文/韩语/英语歌词，希望用对应浏览器 TTS 朗读词汇或短语。
- 用户提供日语歌词，希望额外显示假名、片假名、罗马音。
- 用户提供 QQ 音乐 `_qm.qrc`，希望自动解密歌词并生成点读页。
- 用户提供 `_qm.qrc + _qmRoma.qrc + _qmts.qrc`，需要判断不同歌词轨用途。
- 用户希望导出词表 CSV，人工补充 `zh` 中文释义后重新生成 HTML。
- 用户反馈某个词点击播放不准，需要检查是否加载了 QRC 词级时间轴。

## 不做什么

- 不下载歌曲或歌词。
- 不绕过版权限制分发音频、歌词或切片。
- 不保证 QQ 音乐缓存一定完整；缓存不完整时，应建议用户改用完整 `.lrc + mp3/flac`，再用 `_qm.qrc` 补词级时间。
- 不做专业字幕对轴编辑；如果 LRC 时间轴本身不准，需要用户提供更准确歌词或手工修正。

## 标准工作流程

### 1. 判断输入类型

优先确认用户给了哪些文件：

| 输入组合 | 推荐处理 |
|---|---|
| `.txt` | 生成无原唱音频的词汇/短语点读页 |
| `.lrc` | 解析整首行级时间轴，可配合音频切句 |
| `.lrc + mp3/flac` | 推荐方案，生成完整逐句原唱 |
| `_qm.qrc` | 可解密 QQ QRC，但可能只有部分行 |
| `.lrc + mp3/flac + _qm.qrc` | 最佳方案：LRC 做整句，QRC 做词级点击 |

### 2. 安装依赖

在项目根目录运行：

```powershell
pip install -r .cursor/skills/multilingual-lyrics-reader/assets/requirements.txt
```

如果只是生成基本 HTML，缺少 SudachiPy 时仍会降级运行；非日语语言默认使用通用分词器。如果需要切音频，必须能使用 ffmpeg，`imageio-ffmpeg` 会提供兜底。

### 3. 生成 HTML

最常用命令：

```powershell
python .cursor/skills/multilingual-lyrics-reader/scripts/build_reader.py `
  --lyrics "c:\Users\Administrator\Music\某首歌.lrc" `
  --audio "c:\Users\Administrator\Music\某首歌.mp3" `
  --language yue `
  --speech-lang zh-HK `
  --title "某首歌 点读" `
  --out "生成结果输出/lyrics_readers/song_reader.html" `
  --export-vocab "生成结果输出/lyrics_readers/song_vocab.csv"
```

如需显式指定 QQ 音乐词级时间轴：

```powershell
python .cursor/skills/multilingual-lyrics-reader/scripts/build_reader.py `
  --lyrics "c:\Users\Administrator\Music\某首歌.lrc" `
  --audio "c:\Users\Administrator\Music\某首歌.mp3" `
  --qrc-timing "e:\QQMusicCache\QQMusicLyricNew\某首歌_qm.qrc" `
  --title "某首歌 点读" `
  --out "生成结果输出/lyrics_readers/song_reader.html"
```

### 4. 校对中文释义

首次运行时使用 `--export-vocab` 导出 CSV。用户编辑 `zh` 列后，再用 `--vocab` 重新生成：

```powershell
python .cursor/skills/multilingual-lyrics-reader/scripts/build_reader.py `
  --lyrics "c:\Users\Administrator\Music\某首歌.lrc" `
  --audio "c:\Users\Administrator\Music\某首歌.mp3" `
  --vocab "生成结果输出/lyrics_readers/song_vocab.csv" `
  --title "某首歌 点读" `
  --out "生成结果输出/lyrics_readers/song_reader.html"
```

## 输出产物

| 产物 | 说明 |
|---|---|
| `song_reader.html` | 点读页面 |
| `song_reader_audio/line_000.mp3` 等 | 按句切分的原唱片段 |
| `song_vocab.csv` | 可人工校对的词表 |
| `tokens.json`（可选） | 分词与时间轴结构化数据 |

HTML 交互：

- 行首 `▶`：播放整句原唱。
- 点击词汇：有 QRC 词级时间轴时播放该词原唱片段；否则使用当前语言的浏览器 TTS。
- 拖选多个词：用浏览器 TTS 朗读短语。
- 侧栏：显示/隐藏读音、罗马化/转写、中文。

## 参数速查

| 参数 | 必需 | 说明 |
|---|---|---|
| `--lyrics` | 是 | `.txt` / `.lrc` / 明文 QRC XML / 加密 `_qm.qrc` |
| `--out` | 是 | 输出 HTML |
| `--title` | 否 | 页面标题 |
| `--vocab` | 否 | 已校对 CSV |
| `--export-vocab` | 否 | 导出 CSV |
| `--tokens-out` | 否 | 导出 JSON |
| `--audio` | 否 | 音频文件 |
| `--audio-padding` | 否 | 每句音频前后预留毫秒数，默认 `80` |
| `--qrc-timing` | 否 | QQ `_qm.qrc`，提供词级原唱点击 |
| `--language` | 否 | 歌词语言，如 `ja`、`yue`、`zh-CN`、`ko`、`en`，默认 `auto` |
| `--speech-lang` | 否 | 浏览器 TTS 语言标签，如 `ja-JP`、`zh-HK`、`ko-KR`、`en-US` |

## 故障排查

### 点击词汇播放的是机器音

说明没有可用词级时间轴。处理顺序：

1. 确认是否有匹配的 `_qm.qrc`。
2. 重新运行时加 `--qrc-timing "...\xxx_qm.qrc"`。
3. 生成后在 HTML 数据里检查 token 是否有 `startMs` / `durationMs`。

### 只有前几句能逐词播放原唱

QQ 缓存 `_qm.qrc` 可能只保存了部分 QRC 行。整句仍由 LRC + 音频保证完整；词级播放只覆盖 QRC 里存在的部分。

### 句段音频错位

优先检查 LRC 对轴是否准确。可以调整：

```powershell
--audio-padding 120
```

如果整体固定偏移，应先修正 LRC 的 `[offset:]` 或时间戳。

### 中文释义为空

这是正常的首次导出状态。编辑 `--export-vocab` 生成的 CSV，在 `zh` 列补充释义，再用 `--vocab` 重跑。

### 粤语/韩语/英语发音不对

显式指定 `--speech-lang`：

```powershell
--language yue --speech-lang zh-HK
--language ko --speech-lang ko-KR
--language en --speech-lang en-US
```

浏览器和系统必须安装对应语音包，否则可能回退到系统默认语音。

## 文件结构

```text
multilingual-lyrics-reader/
├── SKILL.md
├── scripts/
│   ├── build_reader.py
│   ├── audio_splitter.py
│   ├── qrc_decoder.py
│   ├── qq_des.py
│   ├── qq_des_tables.py
│   └── word_timing.py
├── references/
│   └── USAGE_GUIDE.md
└── assets/
    ├── requirements.txt
    ├── sample_lyrics.txt
    └── sample_vocab.csv
```

## 注意事项

- 生成内容仅用于个人学习。
- 不要公开分享受版权保护的歌词、歌曲音频或切分片段。
- Windows 中文路径下，命令参数必须用双引号包裹。
- HTML 与 `*_audio/` 文件夹必须保持相对位置不变。
