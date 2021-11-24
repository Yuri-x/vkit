from pprint import pprint
from collections import defaultdict
import logging
import string

import iolite as io
import opencc

from vkit.text.lexicon.opt import (
    normalize,
    get_lexicon_type,
    LexiconType,
)
from vkit.text.lexicon.const.chinese import CHINESE_RADICAL
from vkit.text.lexicon.const.delimiter import DELIMITER_BLACKLIST

logger = logging.getLogger(__name__)


def load_unihan(unihan_json):
    items = io.read_json(io.file(unihan_json, exists=True))
    char_to_item = {item['char']: item for item in items}
    return char_to_item


def extract_radicals_from_unihan(unihan_json):
    char_to_item = load_unihan(unihan_json)

    radicals = []
    for char, item in char_to_item.items():
        is_radical = False
        for definition in item.get('kDefinition', []):
            if 'radical' in definition.lower():
                is_radical = True
                break
        if is_radical:
            radicals.append(char)

    pprint(sorted(radicals))


def extract_black_list_from_unihan(unihan_json, output):
    char_to_item = load_unihan(unihan_json)

    with_compatibility_variant_chars = []
    for char, item in char_to_item.items():
        if item.get('kCompatibilityVariant'):
            with_compatibility_variant_chars.append(char)

    io.write_json(
        io.file(output),
        with_compatibility_variant_chars,
        indent=2,
        ensure_ascii=False,
    )


def inspect_opencc_cvt_drop(opencc_cvt, chars, output_json):
    original = set(chars)
    preserved = set()
    removed = set()
    new = set()

    for char in chars:
        transformed_char = opencc_cvt.convert(char)
        assert len(transformed_char) == 1
        if transformed_char == char:
            preserved.add(char)
        else:
            removed.add(char)
            if transformed_char not in original:
                new.add(transformed_char)
            else:
                preserved.add(transformed_char)

    preserved = sorted(list(preserved))
    removed = sorted(list(removed))
    new = sorted(list(new))
    io.write_json(
        output_json,
        {
            'num_original': len(original),
            'num_preserved': len(preserved),
            'num_removed': len(removed),
            'num_new': len(new),
            'preserved': preserved,
            'removed': removed,
            'new': new,
        },
        ensure_ascii=False,
        indent=2,
    )


def inspect_charset_cvt_drop(chars_txts, output_json, mode='t2s'):
    chars = set()
    for chars_txt in chars_txts.split(','):
        for char in io.read_text_lines(chars_txt, strip=True):
            if len(char) != 1:
                logger.warning(f'Ignore char={char}')
                continue
            chars.add(char)
    chars = sorted(list(chars))

    inspect_opencc_cvt_drop(opencc.OpenCC(f'{mode}.json'), chars, output_json)


def process_tygfbs_txt(tygfbs_txt, output_txt):
    chars = set()
    for line in io.read_text_lines(
        tygfbs_txt,
        strip=True,
        skip_empty=True,
    ):
        chars.update(line)

    io.write_text_lines(output_txt, chars)


def load_chars_txt(chars_txt):
    return set(io.read_text_lines(
        chars_txt,
        strip=True,
        skip_empty=True,
    ))


def build_lexicons(
    ppocr_keys_v1_txt,
    gb2312_txt,
    tygfbs_txt,
    customized_txt,
    customized_aliases_txt,
    charset,
    unihan_black_list_json,
    customized_black_list_txt,
    output,
):
    # Candidates.
    ppocr_keys_v1_chars = load_chars_txt(ppocr_keys_v1_txt)
    gb2312_chars = load_chars_txt(gb2312_txt)
    tygfbs_chars = load_chars_txt(tygfbs_txt)
    customized_chars = load_chars_txt(customized_txt)

    combined_chars = set()
    combined_chars.update(ppocr_keys_v1_chars)
    combined_chars.update(gb2312_chars)
    combined_chars.update(tygfbs_chars)
    combined_chars.update(customized_chars)

    # Convert to simplified only chars.
    simp_chars = set()
    opencc_t2s_cvt = opencc.OpenCC('t2s.json')
    for char in combined_chars:
        char = opencc_t2s_cvt.convert(char)
        if len(char) != 1:
            continue
        simp_chars.add(char)

    # Convert to traditional only chars.
    trad_chars = set()
    opencc_s2t_cvt = opencc.OpenCC('s2t.json')
    for char in combined_chars:
        char = opencc_s2t_cvt.convert(char)
        if len(char) != 1:
            continue
        trad_chars.add(char)

    # Pick based on charset.
    if charset == 'simp':
        # Combine.
        raw_chars = simp_chars | gb2312_chars
    elif charset == 'simp-trad':
        # For simplified & traditional chinese.
        raw_chars = combined_chars | simp_chars | trad_chars
    else:
        raise NotImplementedError()

    removed = []

    # Build alias.
    char_to_aliases = defaultdict(set)
    visited_chars = set()

    # Load customized aliases.
    if customized_aliases_txt:
        for line in io.read_text_lines(customized_aliases_txt, strip=True, skip_empty=True):
            chars = line.split()
            for char in chars:
                assert len(char) == 1 and normalize(char) == char
            # Head as norm.
            assert chars[0] in chars[1:]
            norm_char = chars[0]
            aliases = [char for char in chars[1:] if char != norm_char]
            logger.info(f'char={norm_char}, aliases={aliases}')
            char_to_aliases[norm_char].update(aliases)
            visited_chars.update(chars)

    for char in raw_chars:
        assert char

        if char in visited_chars:
            logger.info(f'char={char} has been processed, skip')
            continue
        visited_chars.add(char)

        norm_char = normalize(char)
        if len(norm_char) != 1:
            # i.e. 'Ⅳ' -> 'IV'
            removed.append((char, 'length != 1'))
            continue

        # Touch.
        char_to_aliases[norm_char]
        # Add alias.
        if char != norm_char:
            if get_lexicon_type(char) != LexiconType.UNKNOWN:
                char_to_aliases[norm_char].add(char)
            else:
                removed.append((char, 'is unknown type'))
        # Add fullwidth version if exists.
        if 0x21 <= ord(norm_char) <= 0x7E:
            char_to_aliases[norm_char].add(chr(ord(norm_char) + 0xFEE0))

    # Filter based on unihan.
    unihan_black_list = set(io.read_json(unihan_black_list_json))
    customized_black_list = load_chars_txt(customized_black_list_txt)

    target_lexicon_types = {
        LexiconType.DELIMITER,
        LexiconType.DIGIT,
        LexiconType.ENGLISH,
        LexiconType.CHINESE,
    }

    # To make sure ASCII chars are covered.
    ascii_chars = set(chr(cp) for cp in range(0x21, 0x7F))

    lexicons = []
    tag_chinese = False

    for char, aliases in sorted(char_to_aliases.items(), key=lambda p: p[0]):
        lexicon_type = get_lexicon_type(char)

        # Filtering.
        remove_reason = None

        if lexicon_type not in target_lexicon_types:
            remove_reason = 'not in target_lexicon_types'
        elif char in CHINESE_RADICAL:
            remove_reason = 'in CHINESE_RADICAL'
        elif char in DELIMITER_BLACKLIST:
            remove_reason = 'in DELIMITER_BLACKLIST'
        elif char in unihan_black_list:
            remove_reason = 'in unihan_black_list'
        elif char in customized_black_list:
            remove_reason = 'in customized_black_list'

        if remove_reason:
            removed.append((char, remove_reason))
            removed.extend((alias, f'alias of char={char}:' + remove_reason) for alias in aliases)
            continue

        assert char not in aliases

        # Tagging.
        if char == '㐂':
            # All chars after 㐂 are chinese.
            tag_chinese = True

        if char == '〇' or tag_chinese:
            tag = 'chinese'
        elif char in string.ascii_letters:
            tag = 'english'
        elif char in string.digits:
            tag = 'digit'
        else:
            tag = 'delimiter'

        lexicon_type_name = lexicon_type.name.lower()
        if tag != lexicon_type_name:
            logger.warning(f'char={char} tag={tag} != {lexicon_type_name}')

        lexicons.append({'char': char, 'aliases': sorted(aliases), 'tag': tag})

        if char in ascii_chars:
            ascii_chars.remove(char)

    assert not ascii_chars

    # Check s2t & t2s is well-defined on lexicons.
    all_chars = set()
    for lexicon in lexicons:
        all_chars.add(lexicon['char'])
        all_chars.update(lexicon['aliases'])

    for char in all_chars:
        if opencc_s2t_cvt.convert(char) not in all_chars:
            logger.warning(f'char={char} invalid s2t={opencc_s2t_cvt.convert(char)}')
        if opencc_t2s_cvt.convert(char) not in all_chars:
            logger.warning(f'char={char} invalid t2s={opencc_t2s_cvt.convert(char)}')

    removed_dump = '\n'.join(map(str, sorted(removed)))
    logger.info(f'Remove chars: \n{removed_dump}')

    if charset == 'simp':
        only_in_gb2312 = set()
        only_in_simp_chars = set()
        for lexicon in lexicons:
            char = lexicon['char']
            if char in simp_chars and char not in gb2312_chars:
                only_in_simp_chars.add(char)
            if char not in simp_chars and char in gb2312_chars:
                only_in_gb2312.add(char)

        # For simplified chinese.
        logger.info('chars not in simp_chars but in GB2312:')
        for idx, char in enumerate(only_in_gb2312):
            # i.e. '乾'
            logger.info(f'{idx}: {char}')
        logger.info('chars in simp_chars but not in GB2312:')
        for idx, char in enumerate(only_in_simp_chars):
            logger.info(f'{idx}: {char}')

    io.write_json_lines(io.file(output), lexicons, ensure_ascii=False)


def load_ununified_raw_and_compare_with_lexicons(dict_jsl, ununified_raw_txt, output_txt):
    groups = []
    for line in io.read_text_lines(ununified_raw_txt, strip=True, skip_empty=True):
        chunks = line.split()
        assert len(chunks) in (4, 6)
        chars = []
        idx = 1
        while idx < len(chunks):
            char = normalize(chunks[idx])
            assert len(char) == 1
            assert char not in chars
            chars.append(char)
            idx += 2
        groups.append(chars)

    all_chars = set()
    for lexicon in io.read_json_lines(dict_jsl):
        all_chars.add(lexicon['char'])
        all_chars.update(lexicon['aliases'])

    out = []
    for chars in groups:
        hit_chars = []
        for char in chars:
            if char in all_chars:
                hit_chars.append(char)
        if len(hit_chars) > 1:
            # Need to manually decide the norm char.
            out.append(' ' + ' '.join(hit_chars))

    io.write_text_lines(output_txt, out)


def compare_lexicons(prev, cur):
    prev_chars = {item['char'] for item in io.read_json_lines(io.file(prev, exists=True))}
    cur_chars = {item['char'] for item in io.read_json_lines(io.file(cur, exists=True))}

    logger.info(f'IN PREV ONLY: {sorted(prev_chars - cur_chars)}')
    logger.info(f'IN CUR ONLY: {sorted(cur_chars - prev_chars)}')
