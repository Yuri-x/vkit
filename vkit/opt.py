import subprocess
import iolite as io

from vkit.type import PathType


def get_data_folder(file: PathType):
    proc = subprocess.run(
        f'pyproject-data-folder "$VKIT_ROOT" "$VKIT_DATA" "{file}"',
        shell=True,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0

    data_folder = proc.stdout.strip()
    assert data_folder

    io.folder(data_folder, touch=True)

    return data_folder
