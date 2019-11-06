from os.path import split
from offline_trans.util import set_current_dir
from pathlib import Path
import tempfile
import subprocess
from typing import Tuple, AnyStr, Union
import os

base_path = Path(__file__).parent.absolute().joinpath('fixtures')

def get_docker_tar(image_name:str='dokcer-manifest', version:str= "1.0") -> Union[str, Path]:
    return base_path.joinpath('docker_images').joinpath(f'{image_name}_v{version.replace(".", "_")}.tar')


def setup_package():
    """
    use fixtures as base directory
    """
    set_current_dir(base_path)

    # build image
    p1 = subprocess.run('docker build -t offline_trans:v1 -f Dockerfile.v1 .', cwd=base_path.joinpath('docker_files'), shell=True)
    p2 = subprocess.run('docker build -t offline_trans:v2 -f Dockerfile.v2 .', cwd=base_path.joinpath('docker_files'), shell=True)

    p3 = subprocess.run(f'docker save -o {base_path.joinpath("docker_images").joinpath("offline_trans_v1.tar")} offline_trans:v1', shell=True)
    p4 = subprocess.run(f'docker save -o {base_path.joinpath("docker_images").joinpath("offline_trans_v2.tar")} offline_trans:v1', shell=True)

    if any(map((lambda p: p.returncode!=0), (p1, p2, p3, p4))):
        raise RuntimeError('cannot prepare required files')