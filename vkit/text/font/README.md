```bash
export FONT_DATA=$(pyproject-data-folder "$VKIT_ROOT" "$VKIT_DATA" vkit/text/font)
```

收集字体文件（OTF/TTF/TTC)：

```bash
mkdir "${FONT_DATA}/font_download"
git clone https://github.com/dolbydu/font.git
mv font/unicode "${FONT_DATA}/font_download/chinese-font-1"

# Download Chinese Google fonts.
mkdir "${FONT_DATA}/font_download/chinese-font-2"

# Download https://github.com/Haixing-Hu/latex-chinese-fonts
mkdir "${FONT_DATA}/font_download/chinese-font-3"

# https://github.com/wang-tf/Chinese_OCR_synthetic_data/tree/master/fonts
mkdir "${FONT_DATA}/font_download/chinese-font-4"

# Copy from windows.
mkdir "${FONT_DATA}/font_download/windows-font"

# chinese-font-pixel：收集的点阵字体

# /System/Library/Fonts: macOS 的系统字体
export FONT_FOLDERS="
/System/Library/Fonts,
${FONT_DATA}/font_download/chinese-font-1,
${FONT_DATA}/font_download/chinese-font-2,
${FONT_DATA}/font_download/chinese-font-3,
${FONT_DATA}/font_download/chinese-font-4,
${FONT_DATA}/font_download/windows-font,
${FONT_DATA}/font_download/chinese-font-pixel
"
```

汇总与去重：

```bash
fib vkit.text.font.builder:flatten_font_files \
    --font_folders="$FONT_FOLDERS" \
    --output="${FONT_DATA}/font_flatten"
```

利用 LaTeX 筛选中文字体：

```bash
# 安装 XeLaTeX
# macOS: http://www.tug.org/mactex/mactex-download.html
# Linux: TODO

# 渲染两句话，根据 xelatex log 判断字体是否支持中文
fib vkit.text.font.builder:classify_chinese_fonts \
    --font_folder="${FONT_DATA}/font_flatten" \
    --render_folder="${FONT_DATA}/render_folder" \
    --output="${FONT_DATA}/classify_chinese_fonts_results.json"

# 保留支持中文的字体
fib vkit.text.font.builder:select_chinese_fonts \
    --cla_results="${FONT_DATA}/classify_chinese_fonts_results.json" \
    --output="${FONT_DATA}/font_chinese"
```

生成字体数据（更新 lexicon 之后不用执行上面的步骤）：

```bash
# 需要基于字符集
export LEXICON_DATA=$(pyproject-data-folder "$VKIT_ROOT" "$VKIT_DATA" vkit/text/lexicon)
```

```bash
# optional.
# 确保以下猜测成立:
# 1. TTF file only contains index=0.
# 2. TTC file contains more than one faces (index > 0).
fib vkit.text.font.builder:check_no_collection_in_ttf --font_folder="${FONT_DATA}/font_chinese"

# 基于 xelatex 探测每个字体支持的字符集
fib vkit.text.font.builder:find_xelatex_supported_chars \
    --font_folder="${FONT_DATA}/font_chinese" \
    --lexicons_json="${LEXICON_DATA}/final.jsl" \
    --render_folder="${FONT_DATA}/render_folder" \
    --output="${FONT_DATA}/font_xelatex_chinese_supported_chars.jsl"

# 基于 freetype 探测每个字体支持的字符集
fib vkit.text.font.builder:find_freetype_supported_chars \
    --font_folder="${FONT_DATA}/font_chinese" \
    --lexicons_json="${LEXICON_DATA}/final.jsl" \
    --render_folder="${FONT_DATA}/render_folder" \
    --output="${FONT_DATA}/font_freetype_chinese_supported_chars.jsl"

# 合并
fib vkit.text.font.builder:combine_supported_chars_jsls \
    --supported_chars_jsls="${FONT_DATA}/font_xelatex_chinese_supported_chars.jsl,${FONT_DATA}/font_freetype_chinese_supported_chars.jsl" \
    --output="${FONT_DATA}/font_combined_chinese_supported_chars.jsl"

# 规则筛选与最终合并
fib vkit.text.font.builder:build_font_index \
    --lexicons_json="${LEXICON_DATA}/final.jsl" \
    --supported_chars_jsl="${FONT_DATA}/font_combined_chinese_supported_chars.jsl" \
    --output="${FONT_DATA}/final"
```
