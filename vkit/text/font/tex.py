import os
import subprocess
import re
import logging

import iolite as io
import jinja2

logger = logging.getLogger(__name__)

TEX_JINJA_ENV = jinja2.Environment(
    variable_start_string=r'{!',
    variable_end_string=r'!}',
    trim_blocks=True,
    lstrip_blocks=True,
    autoescape=False,
    undefined=jinja2.StrictUndefined,
)
TEX_FILE_TEMPLATE_TEXT = r'''
{#
Read:
http://texdoc.net/texmf-dist/doc/latex/fontspec/fontspec.pdf
https://en.wikibooks.org/wiki/LaTeX/Fonts
https://scripts.sil.org/cms/scripts/page.php?site_id=nrsi&id=IWS-Chapter08
#}
\documentclass[varwidth=9999pt]{standalone}
\usepackage{fontspec}
{% if vert_mode  %}
\usepackage{graphicx}
{% endif %}

\setmainfont{{!font_file_name!}}[
    Path = {!font_folder!} ,
    {% if font_index is not none  %}
    {#
        FontIndex:
        Truetype collections index.
    #}
    FontIndex = {!font_index!},
    {% endif %}
    {#
        LetterSpace:
        The letter spacing parameter is a normalised additive factor (not a scaling factor);
        it is defined as a percentage of the font size.
        That is, for a 10 pt font, a letter spacing parameter of ‘1.0’
        will add 0.1 pt between each letter.
        NOTE: negative value for subtraction.
    #}
    LetterSpace = {!letter_space!} ,
    {#
        WordSpace:
        For those times when the precise details are important,
        the WordSpace feature is provided,
        which takes either a single scaling factor to scale the default value,
        or a triplet of comma-separated values to scale the nominal value,
        the stretch, and the shrink of the interword space by, respectively.
        (WordSpace={x} is the same as WordSpace={x,x,x}.)
    #}
    WordSpace = {!word_space!} ,
    {#
        PunctuationSpace:
        The PunctuationSpace feature takes a scaling factor by which
        to adjust the nominal value chosen for the font
    #}
    PunctuationSpace = {!punctuation_space!} ,
    {#
        Color:
        A six-digit hex colour RRGGBB
    #}
    Color = {!rgb_hex!} ,
]

\begin{document}
\fontsize{{!font_size!}pt}{{!font_size + 6!}pt}\selectfont
{!lines!}
\end{document}
'''
TEX_FILE_TEMPLATE = TEX_JINJA_ENV.from_string(TEX_FILE_TEMPLATE_TEXT)

# From https://github.com/JelteF/PyLaTeX/blob/v1.3.2/pylatex/utils.py#L68-L100
LATEX_SPECIAL_CHAR_ESCAPE_MAPPING = {
    '&': r'\&',
    '%': r'\%',
    '$': r'\$',
    '#': r'\#',
    '_': r'\_',
    '{': r'\{',
    '}': r'\}',
    '~': r'\textasciitilde{}',
    '^': r'\^{}',
    '\\': r'\textbackslash{}',
    '\n': '\\newline%\n',
    '-': r'{-}',
    '\xA0': '~',  # Non-breaking space
    '[': r'{[}',
    ']': r'{]}',
}


def check_subprocess_run(result):
    if result.returncode != 0:
        msg = '\n'.join((
            'args:',
            str(result.args),
            'stdout:',
            result.stdout.decode(),
            'stderr:',
            result.stderr.decode(),
        ))
        raise RuntimeError(msg)


class TexRenderBasic:

    def __init__(self, folder, disable_cleanup=False):
        self.id = os.getpid()
        self.fd = io.folder(folder, touch=True)

        self.id_tag_template = f'{self.id}-{{}}'
        self.tex_ext = '.tex'
        self.aux_ext = '.aux'
        self.log_ext = '.log'
        self.pdf_ext = '.pdf'
        self.png_suffix = '-1.png'
        self.disable_cleanup = disable_cleanup

    def tex_filename(self, tag):
        return self.id_tag_template.format(tag) + self.tex_ext

    def log_filename(self, tag):
        return self.id_tag_template.format(tag) + self.log_ext

    def generate_tex_file(
        self,
        text,
        font_file,
        ttc_font_index,
        font_size,
        letter_space,
        word_space,
        punctuation_space,
        rgb_hex,
        tag,
    ):
        font_file = io.file(font_file, exists=True)

        # "Path" must ends with slash.
        font_folder = str(font_file.parent)
        if not font_folder.endswith('/'):
            font_folder += '/'

        # Escape special chars.
        text = ''.join(LATEX_SPECIAL_CHAR_ESCAPE_MAPPING.get(char, char) for char in text)
        tex_file_text = TEX_FILE_TEMPLATE.render(
            font_file_name=font_file.parts[-1],
            font_folder=font_folder,
            font_index=ttc_font_index,
            font_size=font_size,
            letter_space=letter_space,
            word_space=word_space,
            punctuation_space=punctuation_space,
            rgb_hex=rgb_hex,
            vert_mode=False,
            lines=text,
        )
        with open(self.fd / self.tex_filename(tag), 'w') as fout:
            fout.write(tex_file_text)

    def compile_tex_file(self, tag):
        result = subprocess.run(
            ['xelatex', '-halt-on-error', self.tex_filename(tag)],
            cwd=self.fd,
            capture_output=True,
        )
        check_subprocess_run(result)

    def get_not_supported_chars(self, tag):
        with open(self.fd / self.log_filename(tag)) as fin:
            text = fin.read()

        not_supported_chars = set()
        pattern = r'There is no (\S+) in font'
        for match in re.finditer(pattern, text, re.UNICODE):
            char = match.group(1)
            assert len(char) == 1
            not_supported_chars.add(char)
        return not_supported_chars

    def __del__(self):
        if not self.disable_cleanup:
            for path in self.fd.glob(self.id_tag_template.format('*')):
                path.unlink()
