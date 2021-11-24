import logging
from collections import defaultdict
import hashlib
import shutil
import multiprocessing

import iolite as io
from tqdm import tqdm
from PIL import ImageFont
import freetype

from vkit.text.lexicon.type import VLexiconCollection
from vkit.text.font.tex import TexRenderBasic

logger = logging.getLogger(__name__)


def update_hash_algo_with_file(path, hash_alog) -> None:
    with open(path, 'rb') as fin:
        # 64KB block.
        for block in iter(lambda: fin.read(65536), b''):
            hash_alog.update(block)


def calculate_hash(path):
    sha256_algo = hashlib.sha256()
    update_hash_algo_with_file(path, sha256_algo)
    return sha256_algo.hexdigest()


def search_font_files(font_folders, truetype=True, opentype=True, path_only=True):
    exts = []
    if truetype:
        exts.extend(['ttf', 'ttc'])
    if opentype:
        # OTC is ignored since it's not commonly used.
        exts.extend(['otf'])

    for ext in list(exts):
        exts.append(ext.upper())

    # Remove duplicated file.
    hash_to_paths = defaultdict(list)
    for font_folder in font_folders.split(','):
        input_fd = io.folder(font_folder.strip(), exists=True)
        for ext in exts:
            for font_path in input_fd.glob(f'**/*.{ext}'):
                hash_to_paths[calculate_hash(font_path)].append(font_path)

    filename_to_paths = defaultdict(list)
    for paths_with_same_hash in hash_to_paths.values():
        if len(paths_with_same_hash) > 1:
            logger.info(f'paths with same hash: {paths_with_same_hash}')
        path = paths_with_same_hash[0]
        filename_to_paths[path.name].append(path)

    for filename, paths in filename_to_paths.items():
        if len(paths) == 1:
            if path_only:
                yield paths[0]
            else:
                yield paths[0], paths[0].name
            continue

        # Resolue name conflict.
        logger.info(f'resolve conflict: {paths}')
        for idx, path in enumerate(paths):
            prefix, ext = path.name.rsplit('.', maxsplit=1)
            if path_only:
                yield path
            else:
                yield path, f'{prefix}-{idx}.{ext}'


def flatten_font_files(font_folders, output):
    assert ' ' not in output
    output_fd = io.folder(output, touch=True)
    for font_path, flatten_name in search_font_files(font_folders, path_only=False):
        # Remove space in filename.
        flatten_name = '-'.join(flatten_name.split())
        shutil.copyfile(font_path, output_fd / flatten_name)


def classify_chinese_font(args):
    font_file, render_folder = args

    text_sim = '我能吞下玻璃而不伤身体'
    text_tra = '我能吞下玻璃而不傷身體'

    render_basic = TexRenderBasic(render_folder)

    render_basic.generate_tex_file(
        text=text_sim,
        font_file=font_file,
        ttc_font_index=None,
        font_size=10,
        letter_space=0.0,
        word_space=1.0,
        punctuation_space=0.0,
        rgb_hex='000000',
        tag='default',
    )

    runtime_error = False
    try:
        render_basic.compile_tex_file(tag='default')
    except RuntimeError:
        runtime_error = True
    if runtime_error:
        return font_file, False, False, True

    support_sim = not render_basic.get_not_supported_chars(tag='default')

    render_basic.generate_tex_file(
        text=text_tra,
        font_file=font_file,
        ttc_font_index=None,
        font_size=10,
        letter_space=0.0,
        word_space=1.0,
        punctuation_space=0.0,
        rgb_hex='000000',
        tag='default',
    )

    runtime_error = False
    try:
        render_basic.compile_tex_file(tag='default')
    except RuntimeError:
        runtime_error = True
    if runtime_error:
        return font_file, False, False, True

    support_tra = not render_basic.get_not_supported_chars(tag='default')

    return font_file, support_sim, support_tra, False


def classify_chinese_fonts(font_folder, render_folder, output):
    font_files = list(search_font_files(font_folder))
    results = []
    with multiprocessing.Pool() as pool:
        for font_file, support_sim, support_tra, runtime_error in tqdm(
            pool.imap_unordered(
                classify_chinese_font,
                [(font_file, render_folder) for font_file in font_files],
                chunksize=1,
            )
        ):
            results.append({
                'font_file': str(font_file),
                'support_sim': support_sim,
                'support_tra': support_tra,
                'runtime_error': runtime_error,
            })

    io.write_json(io.file(output), results, indent=2)


def select_chinese_fonts(cla_results, output):
    resutls = io.read_json(io.file(cla_results, exists=True))

    assert ' ' not in output
    output_fd = io.folder(output, touch=True)
    for result in resutls:
        if result['support_sim'] or result['support_tra']:
            font_file = result['font_file']

            in_blacklist = False
            for keyword in (
                'ヒ',
                'LastResort',
                'Wingdings',
                'CourierOblique',
            ):
                if keyword in font_file:
                    in_blacklist = True
                    break

            if in_blacklist:
                logger.info(f'In blacklist {font_file}')
                continue

            logger.info(f'Select {font_file}')
            filename = font_file.split('/')[-1]
            shutil.copyfile(font_file, output_fd / filename)


def get_font_index_max(path):
    index = 0
    while True:
        try:
            ImageFont.truetype(
                font=path,
                size=50,
                index=index,
            )
            index += 1
        except OSError:
            break

    return index


def check_no_collection_in_ttf(font_folder):
    ttf_files = []
    ttc_files = []
    for font_file in search_font_files(font_folder, truetype=True, opentype=False):
        if str(font_file).lower().endswith('ttf'):
            ttf_files.append(font_file)
        else:
            ttc_files.append(font_file)

    logger.info('TTF')
    for font_file in ttf_files:
        font_file = str(font_file)
        logger.info(font_file)
        index_max = get_font_index_max(font_file)
        logger.info(index_max)
        assert index_max == 1

    logger.info('=' * 20)

    logger.info('TTC')
    for font_file in ttc_files:
        font_file = str(font_file)
        logger.info(font_file)
        index_max = get_font_index_max(font_file)
        logger.info(index_max)
        assert index_max > 1


def proc_find_xelatex_supported_chars(args):
    font_file, chars, render_folder = args

    not_supported_chars = set()
    chunksize = 100
    begin = 0

    render_basic = TexRenderBasic(render_folder)
    while begin < len(chars):
        end = begin + chunksize
        logger.info(f'{font_file}, [{begin}, {end}]')

        text = ''.join(chars[begin:end])
        render_basic.generate_tex_file(
            text=text,
            font_file=font_file,
            # NOTE: we assume TTC support the same set of chars in every font face.
            ttc_font_index=None,
            font_size=10,
            letter_space=0.0,
            word_space=1.0,
            punctuation_space=0.0,
            rgb_hex='000000',
            tag='default',
        )
        render_basic.compile_tex_file(tag='default')
        not_supported_chars.update(render_basic.get_not_supported_chars(tag='default'))

        begin = end

    return font_file, not_supported_chars


def proc_find_freetype_supported_chars(args):
    font_file, chars, _ = args

    face = freetype.Face(str(font_file), index=0)
    load_char_flags = freetype.FT_LOAD_RENDER  # type: ignore
    load_char_flags |= freetype.FT_LOAD_FORCE_AUTOHINT  # type: ignore
    load_char_flags |= freetype.FT_LOAD_TARGET_LCD  # type: ignore

    base_res = 72
    font_size = 12
    face.set_char_size(
        width=font_size << 6,
        height=0,
        hres=base_res,
        vres=base_res,
    )

    not_supported_chars = []
    for char in chars:
        not_supported = False
        try:
            face.load_char(char, load_char_flags)
            bitmap = face.glyph.bitmap
            if bitmap.rows == 0 or bitmap.width == 0:
                not_supported = True
        except Exception:
            logger.exception('Failed to load_char.')
        if not_supported:
            logger.warning(f'{font_file}: not supported char = {char}')
            not_supported_chars.append(char)

    return font_file, not_supported_chars


def find_supported_chars_based_on_proc_func(
    proc_func,
    font_folder,
    lexicons_json,
    render_folder,
    output,
):
    chars = []
    for lexicon in VLexiconCollection.from_file(lexicons_json).lexicons:
        chars.append(lexicon.char)
        chars.extend(lexicon.aliases)

    results = []
    with multiprocessing.Pool() as pool:
        for font_file, not_supported_chars in tqdm(
            pool.imap_unordered(
                proc_func,
                [(font_file, chars, render_folder) for font_file in search_font_files(font_folder)]
            )
        ):
            results.append((font_file, not_supported_chars))

    out = []
    for font_file, not_supported_chars in results:
        supported_chars = []
        for char in chars:
            if char not in not_supported_chars:
                supported_chars.append(char)
        out.append({
            'font_file': str(font_file),
            'supported_chars': supported_chars,
        })

    io.write_json_lines(io.file(output), out, ensure_ascii=False)


def find_xelatex_supported_chars(font_folder, lexicons_json, render_folder, output):
    find_supported_chars_based_on_proc_func(
        proc_func=proc_find_xelatex_supported_chars,
        font_folder=font_folder,
        lexicons_json=lexicons_json,
        render_folder=render_folder,
        output=output,
    )


def find_freetype_supported_chars(font_folder, lexicons_json, render_folder, output):
    find_supported_chars_based_on_proc_func(
        proc_func=proc_find_freetype_supported_chars,
        font_folder=font_folder,
        lexicons_json=lexicons_json,
        render_folder=render_folder,
        output=output,
    )


def combine_supported_chars_jsls(supported_chars_jsls, output):
    font_file_to_supported_chars_sets = defaultdict(list)
    for supported_chars_jsl in supported_chars_jsls.split(','):
        for line in io.read_json_lines(supported_chars_jsl):
            font_file = line['font_file']
            supported_chars = line['supported_chars']
            font_file_to_supported_chars_sets[font_file].append(set(supported_chars))

    out = []
    for font_file, supported_chars_sets in font_file_to_supported_chars_sets.items():
        union_supported_chars = set.union(*supported_chars_sets)
        intersection_supported_chars = set.intersection(*supported_chars_sets)
        delta = union_supported_chars - intersection_supported_chars
        logger.info(
            f'{font_file}: delta = {len(delta)}, supported = {len(intersection_supported_chars)}'
        )
        out.append({
            'font_file': str(font_file),
            'supported_chars': sorted(intersection_supported_chars),
        })

    io.write_json_lines(io.file(output), out, ensure_ascii=False)


def build_font_index(lexicons_json, supported_chars_jsl, output):
    lexicon_collection = VLexiconCollection.from_file(lexicons_json)

    lexicon_chars = set()
    for lexicon in lexicon_collection.lexicons:
        lexicon_chars.add(lexicon.char)
        lexicon_chars.update(lexicon.aliases)

    post_blacklist = [
        # FZYingBiXingShu-S16T transform simplified char to traditional char.
        'FZYingBiXingShu-S16T',
        'FZYingBiXingShu-S16S',
        # Japanese.
        'AquaKana',
        # Hard to read.
        'ZhiMangXing-Regular',
        'LiuJianMaoCao-Regular',
        # Too fancy.
        'MaShanZheng-Regular',
        'LongCang-Regular',
        'STXingkai',
        'STCaiyun',
        'STHupo',
        'fzmmt',
        # Low quality.
        '方正点阵冯简体',
    ]

    output_fd = io.folder(output, touch=True)
    output_fonts_fd = io.folder(output_fd / 'fonts', reset=True)
    output_font_infos_fd = io.folder(output_fd / 'font_infos', reset=True)

    final_font_infos = []

    # OTF fonts.
    otf_prefix_to_font_infos = defaultdict(list)

    for line in list(io.read_json_lines(io.file(supported_chars_jsl, exists=True))):
        font_file = io.file(line['font_file'], exists=True)

        in_blacklist = False
        for keyword in post_blacklist:
            if keyword in font_file.name:
                in_blacklist = True
                break

        if in_blacklist:
            logger.info(f'{font_file} in blacklist, skip.')
            continue

        # Subset checking.
        assert set(line['supported_chars']) <= lexicon_chars

        font_info = {
            'font_file_name': font_file.name,
            'supported_chars': line['supported_chars'],
        }

        # Copy font files.
        shutil.copyfile(font_file, output_fonts_fd / font_file.name)

        if not font_file.suffix.lower().endswith('.otf'):
            # TTC/TTF.
            font_info['name'] = font_file.stem

            if font_file.suffix.lower() == '.ttc':
                font_info['font_kind'] = 'ttc'
                font_info['ttc_font_index_max'] = get_font_index_max(str(font_file))

            else:
                assert font_file.suffix.lower() == '.ttf'
                font_info['font_kind'] = 'ttf'

            # Save to font infos folder.
            final_font_infos.append(font_info)

        else:
            # Group OTF fonts by prefix.
            otf_prefixes = [
                'Adobe-Fangsong',
                'Adobe-Heiti',
                'Adobe-Kaiti',
                'Adobe-Song',
                'DottedSongti',
                'NotoSansSC',
                'NotoSansTC',
                'NotoSerifSC',
                'NotoSerifTC',
            ]
            hit_otf_prefix = None
            for otf_prefix in otf_prefixes:
                if otf_prefix in font_file.name:
                    assert hit_otf_prefix is None
                    hit_otf_prefix = otf_prefix
            assert hit_otf_prefix

            # Defer.
            otf_prefix_to_font_infos[hit_otf_prefix].append(font_info)

    # Merge OTF font infos.
    for otf_prefix, font_infos in otf_prefix_to_font_infos.items():
        # Assert the same charset.
        supported_chars_sets = [set(font_info['supported_chars']) for font_info in font_infos]
        union_supported_chars = set.union(*supported_chars_sets)
        intersection_supported_chars = set.intersection(*supported_chars_sets)
        assert union_supported_chars == intersection_supported_chars

        # Group.
        font_file_names = [font_info['font_file_name'] for font_info in font_infos]
        otf_font_info = {
            'name': otf_prefix,
            'font_kind': 'votc',
            'font_file_names': font_file_names,
            'supported_chars': font_infos[0]['supported_chars'],
        }
        final_font_infos.append(otf_font_info)

    # Save font infos.
    for final_font_info in final_font_infos:
        io.write_json(
            output_font_infos_fd / f'{final_font_info["name"]}.json',
            final_font_info,
            indent=2,
            ensure_ascii=False,
        )

    # Save lexicon_collection_hash.
    meta = {'lexicon_collection_hash': lexicon_collection.get_hash()}
    logger.info(f'meta = {meta}')
    io.write_json(
        output_fd / 'meta.json',
        meta,
        indent=2,
        ensure_ascii=False,
    )

    # Inspect.
    logger.info('Supported fonts:')
    for font_info in final_font_infos:
        font_info = font_info.copy()
        font_info['supported_chars'] = len(font_info['supported_chars'])
        logger.info(font_info)

    logger.info('MIN 100 char num_supported_fonts')
    char_to_num_supported_fonts = defaultdict(int)
    for font_info in final_font_infos:
        for char in font_info['supported_chars']:
            char_to_num_supported_fonts[char] += 1

    char_num_supported_fonts = sorted(
        char_to_num_supported_fonts.items(),
        key=lambda p: p[1],
    )
    # All char has at least one font for rendering.
    assert char_num_supported_fonts[0][1] > 0
    for char, num_supported_fonts in char_num_supported_fonts[:100]:
        logger.info(f'char={char}, num_supported_fonts={num_supported_fonts}')
