from enum import IntEnum, auto
import itertools
import unicodedata

import intervaltree

from vkit.text.lexicon.const import (
    cjk_compatibility_ideograph,
    chinese,
    english,
    delimiter,
    digit,
    whitespace,
)


def normalize_cjk_fullwidth(text):
    return unicodedata.normalize('NFKC', text)


def normalize_cjk_compatibility_ideograph(text):
    code_points = (ord(char) for char in text)
    normalized_code_points = (
        cjk_compatibility_ideograph.CJK_COMPATIBILITY_IDEOGRAPH.get(code_point, code_point)
        for code_point in code_points
    )
    return ''.join(map(chr, normalized_code_points))


def normalize(text):
    text = normalize_cjk_fullwidth(text)
    text = normalize_cjk_compatibility_ideograph(text)
    return text


class LexiconType(IntEnum):
    CHINESE = auto()
    ENGLISH = auto()
    DELIMITER = auto()
    DIGIT = auto()
    WHITESPACE = auto()
    UNKNOWN = auto()


def add_intervals(itv_tree, nested_intervals, lexicon_type):
    intervals = itertools.chain.from_iterable(nested_intervals)
    for begin, end in intervals:
        # NOTE: adding one since the interval is inclusive.
        itv_tree.addi(begin, end + 1, lexicon_type)


def _build_lexicon_type_itv_tree():
    itv_tree = intervaltree.IntervalTree()

    add_intervals(itv_tree, chinese.ITV_CHINESE, LexiconType.CHINESE)
    add_intervals(itv_tree, english.ITV_ENGLISH, LexiconType.ENGLISH)
    add_intervals(itv_tree, digit.ITV_DIGIT, LexiconType.DIGIT)
    add_intervals(itv_tree, delimiter.ITV_DELIMITER, LexiconType.DELIMITER)
    add_intervals(itv_tree, whitespace.ITV_WHITESPACE, LexiconType.WHITESPACE)

    # Make sure there's no overlap.
    sorted_intervals = sorted(itv_tree, key=lambda itv: itv.begin)  # type: ignore
    idx = 1
    while idx < len(sorted_intervals):
        assert sorted_intervals[idx - 1].end <= sorted_intervals[idx].begin  # type: ignore
        idx += 1

    return itv_tree


_lexicon_type_itv_tree = _build_lexicon_type_itv_tree()


def get_lexicon_type(char):
    lexicon_types = _lexicon_type_itv_tree[ord(char)]
    if not lexicon_types:
        return LexiconType.UNKNOWN
    else:
        assert len(lexicon_types) == 1
        return next(iter(lexicon_types)).data


def debug():
    print(ord(normalize('￥')))
    print(ord(normalize('¥')))
    print(normalize('²②'))
    print(normalize('凉'))
    print(normalize('…'))
    print(normalize('″'))
    print(normalize('´'))

    text = '这是1个！々〓〒〆¥￥〈〉《》「」『』【】〔〕〖〗￠￡〇²②涼…𠡠'
    for char in text:
        print(char, get_lexicon_type(char))
