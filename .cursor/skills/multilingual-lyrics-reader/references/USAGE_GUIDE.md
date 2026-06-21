# 多语言歌词点读工具使用指南

## 功能概览

`multilingual-lyrics-reader` 将多语言歌词转换为可本地打开的 HTML 点读页：

- 将中文/粤语、日语、韩语、英语等歌词切分为词汇级或短语级块。
- 显示原文、读音、罗马化/转写、中文释义。
- 支持 CSV 导出/回填中文释义。
- 支持 `.txt` / `.lrc` / 明文 QRC XML / QQ 音乐加密 `_qm.qrc`。
- 支持传入音频文件，按 LRC/QRC 行级时间轴切分为每句原唱。
- 若能找到 `_qm.qrc` 词级时间轴，点击词汇可播放原唱中该词片段。
- 日语会启用 SudachiPy、假名和罗马音增强；其他语言使用通用分词和指定 TTS 语言。

## 依赖

```powershell
pip install -r .cursor/skills/multilingual-lyrics-reader/assets/requirements.txt
```

依赖说明：

- `sudachipy` + `sudachidict_core`：日语分词与读音增强。
- `imageio-ffmpeg`：系统无 ffmpeg 时提供可用的 ffmpeg 可执行文件。
- `pycantonese`：粤语分词与粤拼（Jyutping）。
- `opencc-python-reimplemented`：简体粤语歌词转香港繁体后再生成粤拼，提高命中率。

如果 SudachiPy 不可用，日语会降级为通用分词；如果 pycantonese 不可用，粤语会降级为通用分词且不会自动显示粤拼。

## 基础命令

### 纯歌词生成 HTML

```powershell
python .cursor/skills/multilingual-lyrics-reader/scripts/build_reader.py `
  --lyrics ".cursor/skills/multilingual-lyrics-reader/assets/sample_lyrics.txt" `
  --vocab ".cursor/skills/multilingual-lyrics-reader/assets/sample_vocab.csv" `
  --language ja `
  --title "歌词点读 Demo" `
  --out "生成结果输出/lyrics_readers/sample_reader.html" `
  --export-vocab "生成结果输出/lyrics_readers/sample_vocab_export.csv"
```

### LRC + MP3 生成整首逐句原唱

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

生成：

```text
song_reader.html
song_reader_audio/
  line_000.mp3
  line_001.mp3
  ...
```

HTML 与 `*_audio/` 文件夹必须保持在同一目录。

### 指定 QQ 音乐 `_qm.qrc` 词级时间轴

当 `.lrc` 提供完整行级时间轴，而 QQ 音乐缓存里另有 `_qm.qrc` 时，可显式指定：

```powershell
python .cursor/skills/multilingual-lyrics-reader/scripts/build_reader.py `
  --lyrics "c:\Users\Administrator\Music\某首歌.lrc" `
  --audio "c:\Users\Administrator\Music\某首歌.mp3" `
  --qrc-timing "e:\QQMusicCache\QQMusicLyricNew\某首歌_qm.qrc" `
  --title "某首歌 点读" `
  --out "生成结果输出/lyrics_readers/song_reader.html"
```

如果不指定 `--qrc-timing`，脚本会尝试在常见 QQ 音乐缓存目录中自动匹配：

- `C:\QQMusicCache\QQMusicLyricNew`
- `D:\QQMusicCache\QQMusicLyricNew`
- `E:\QQMusicCache\QQMusicLyricNew`
- `F:\QQMusicCache\QQMusicLyricNew`
- `G:\QQMusicCache\QQMusicLyricNew`
- `%USERPROFILE%\QQMusicCache\QQMusicLyricNew`

## 参数说明

| 参数 | 必需 | 说明 |
|---|---|---|
| `--lyrics` | 是 | 歌词文件，支持 `.txt`、`.lrc`、明文 `.qrc/.xml`、加密 `_qm.qrc` |
| `--out` | 是 | 输出 HTML 路径 |
| `--title` | 否 | HTML 标题 |
| `--vocab` | 否 | 已校对词表 CSV |
| `--export-vocab` | 否 | 导出待校对词表 CSV |
| `--tokens-out` | 否 | 导出分词 JSON |
| `--audio` | 否 | 歌曲音频，支持 ffmpeg 可读格式 |
| `--audio-padding` | 否 | 每句音频前后额外保留毫秒数，默认 `80` |
| `--qrc-timing` | 否 | QQ 音乐 `_qm.qrc`，用于词级原唱点击 |
| `--language` | 否 | 歌词语言，如 `ja`、`yue`、`zh-CN`、`ko`、`en`，默认 `auto` |
| `--speech-lang` | 否 | 浏览器 TTS 语言标签，如 `ja-JP`、`zh-HK`、`ko-KR`、`en-US` |

## CSV 字段

```csv
surface,lemma,hira,kata,romaji,zh
君,君,きみ,キミ,kimi,你
```

字段：

- `surface`：歌词中出现的词形。
- `lemma`：词典形。
- `hira`：读音字段；日语中为平假名，其他语言可留空或人工填音标/读法。
- `kata`：转写字段；日语中为片假名，其他语言可留空或人工填辅助读音。
- `romaji`：罗马化字段；日语自动生成罗马音，粤语自动生成粤拼，其他语言可人工填拼音、韩语罗马化、IPA 等。
- `zh`：中文释义，可人工校对。

## HTML 交互

- 点击行首 `▶`：播放整句原唱。
- 点击词汇：若有 `_qm.qrc` 词级时间轴，播放原唱中该词片段；否则使用当前语言浏览器 TTS。
- 鼠标拖选多个词：按短语整体朗读（浏览器 TTS）。
- 侧栏可显示/隐藏读音、罗马化/转写、中文。

## 常见问题

### 点击词汇播放不准

优先检查是否加载了匹配的 `_qm.qrc`：

- `.lrc` 只提供行级时间轴，无法精确到词。
- `_qm.qrc` 缓存可能不完整，只能覆盖前几句。
- 可用 `--qrc-timing` 显式指定正确 QRC。

### 只能生成少量句段

如果使用 `_qm.qrc` 作为主歌词，句数取决于 QQ 缓存完整性。完整歌曲更推荐用 `.lrc + mp3` 生成整首逐句音频，再用 `_qm.qrc` 仅补充词级时间轴。

### 中文显示乱码

脚本会按 `utf-8-sig`、`utf-16`、`utf-16-le`、`utf-16-be`、`gb18030` 顺序尝试读取。若仍乱码，先将歌词另存为 UTF-8。

## 版权注意

本工具用于个人语言学习。不要公开分发受版权保护的歌词、歌曲音频或切分后的音频片段。
