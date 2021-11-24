from typing import Sequence, Optional

import attr
import iolite as io

from vkit.type import PathType


class VFontKind:
    TTF = 'ttf'
    TTC = 'ttc'
    # OTC is ignored since it's not commonly used.
    # Hence we manually group the otf collection during the building process.
    VOTC = 'votc'


@attr.define
class VFont:
    name: str
    font_kind: VFontKind
    supported_chars: Sequence[str]
    ttc_font_index_max: Optional[int]
    font_paths: Sequence[str]


@attr.define
class VFontCollection:
    fonts: Sequence[VFont]
    lexicon_collection_hash: str

    @staticmethod
    def from_folder(folder: PathType):
        in_fd = io.folder(folder, exists=True)
        font_infos_fd = in_fd / 'font_infos'
        fonts_fd = in_fd / 'fonts'

        fonts = []
        for font_info_json in font_infos_fd.glob('*.json'):
            font_info = io.read_json(font_info_json)
            font_kind = font_info['font_kind']

            font = VFont(
                name=font_info['name'],
                font_kind=font_kind,
                supported_chars=font_info['supported_chars'],
                ttc_font_index_max=None,
                font_paths=[],
            )

            if font_kind == VFontKind.TTF:
                font = attr.evolve(
                    font,
                    font_paths=[fonts_fd / font_info['font_file_name']],
                )

            elif font_kind == VFontKind.TTC:
                font = attr.evolve(
                    font,
                    ttc_font_index_max=font_info['ttc_font_index_max'],
                    font_paths=[fonts_fd / font_info['font_file_name']],
                )

            else:
                assert font_kind == VFontKind.VOTC
                font_paths = [
                    fonts_fd / font_file_name for font_file_name in font_info['font_file_names']
                ]
                font = attr.evolve(
                    font,
                    font_paths=font_paths,
                )

            fonts.append(font)

        lexicon_collection_hash = io.read_json(in_fd / 'meta.json')['lexicon_collection_hash']

        return VFontCollection(
            fonts=fonts,
            lexicon_collection_hash=lexicon_collection_hash,
        )
