```bash
export LEXICON_DATA=$(pyproject-data-folder "$VKIT_ROOT" "$VKIT_DATA" vkit/text/lexicon)
```

去除异体字：

```bash
# 下载 unihan 数据
pip install unihan-etl==0.13.0
unihan-etl -F json --destination "${LEXICON_DATA}/unihan.json"

# 打印偏旁部首，手动整合进 vkit.text.lexicon.const.cinese.CHINESE_RADICAL
fib vkit.text.lexicon.builder:extract_radicals_from_unihan \
    --unihan_json="${LEXICON_DATA}/unihan.json"

# 将 kCompatibilityVariant （异体字）作为 blacklist，清洗出 lexicon
fib vkit.text.lexicon.builder:extract_black_list_from_unihan \
    --unihan_json="${LEXICON_DATA}/unihan.json" \
    --output="${LEXICON_DATA}/unihan_blacklist.json"
```

候选字典：

```bash
# 下载通用规范汉字笔顺规范
# http://www.moe.gov.cn/jyb_sjzl/ziliao/A19/202103/W020210318300204215237.pdf
# 保存至 ${LEXICON_DATA}/W020210318300204215237.pdf
# 然后从中提取所有字符
pdftotext "${LEXICON_DATA}/W020210318300204215237.pdf" "${LEXICON_DATA}/raw-tygfbs.txt"
# 去重
fib vkit.text.lexicon.builder:process_tygfbs_txt \
    --tygfbs_txt="${LEXICON_DATA}/raw-tygfbs.txt" \
    --output_txt="${LEXICON_DATA}/tygfbs.txt"

# 下载 PaddleOCR 中文字典
wget \
    "https://raw.githubusercontent.com/PaddlePaddle/PaddleOCR/develop/ppocr/utils/ppocr_keys_v1.txt" \
    -O "${LEXICON_DATA}/ppocr_keys_v1.txt"
# 下载 GB2312 字典
wget \
    "https://raw.githubusercontent.com/rime-aca/character_set/master/GB2312.txt" \
    -O "${LEXICON_DATA}/gb2312.txt"
```

```bash
# 观察繁简转换中的字符变更
fib vkit.text.lexicon.builder:inspect_charset_cvt_drop \
    --chars_txts="${LEXICON_DATA}/ppocr_keys_v1.txt,${LEXICON_DATA}/gb2312.txt,${LEXICON_DATA}/tygfbs.txt,${LEXICON_DATA}/customized.txt" \
    --output_json="${LEXICON_DATA}/inspect_charset_t2s_drop.json" \
    --mode="t2s"

# 最终清洗，输出
# customized_txt: 手动添加字符
# customized_aliases_txt: 手动添加的关联字符
# unihan_black_list_json: 清除异体字
# customized_black_list: 手动去除字符
fib vkit.text.lexicon.builder:build_lexicons \
    --ppocr_keys_v1_txt="${LEXICON_DATA}/ppocr_keys_v1.txt" \
    --gb2312_txt="${LEXICON_DATA}/gb2312.txt" \
    --tygfbs_txt="${LEXICON_DATA}/tygfbs.txt" \
    --customized_txt="${LEXICON_DATA}/customized.txt" \
    --customized_aliases_txt="${LEXICON_DATA}/ununified-conflicts-resolved.txt" \
    --charset='simp-trad' \
    --unihan_black_list_json="${LEXICON_DATA}/unihan_blacklist.json" \
    --customized_black_list_txt="${LEXICON_DATA}/customized_black_list.txt" \
    --output="${LEXICON_DATA}/final.jsl"

# final.jsl 结构
# {"char": "1", "aliases": ["①", "１"], "tag": "digit"}
```

继续处理异体字：

```bash
# 从这个 wiki 页面收集异体字
# https://zh.wikipedia.org/wiki/%E6%9C%AA%E7%B5%B1%E4%B8%80%E6%BC%A2%E5%AD%97%E5%88%97%E8%A1%A8
# 保存至 ${LEXICON_DATA}/ununified-raw.txt

# 处理文件。注意：需要将上一步的字典传入此处，螺旋上升，与现有 aliases 合并.
fib vkit/text/lexicon/builder.py:load_ununified_raw_and_compare_with_lexicons \
    --dict_jsl="${LEXICON_DATA}/final.jsl" \
    --ununified_raw_txt="${LEXICON_DATA}/ununified-raw.txt" \
    --output_txt="${LEXICON_DATA}/ununified-conflicts.txt"

# 手动在行首填入标准化字符，保存为 ${LEXICON_DATA}/ununified-conflicts-resolved.txt
# 然后再执行上一步
```
