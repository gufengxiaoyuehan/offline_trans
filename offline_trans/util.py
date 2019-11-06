import json
import logging
import os
import subprocess
from enum import Enum
from io import BytesIO
from pathlib import Path
from shlex import split
from subprocess import CompletedProcess
from tarfile import TarInfo
from typing import IO, List, Optional, Tuple, Union

from offline_trans.docker_archive import MANIFEST_FILE

CUR_DIR = Path('.').resolve()

class TarCategory(Enum):
    BASE = 'base'
    DIFF = 'diff'
    NEW = 'new'

def set_current_dir(path):
    global CUR_DIR
    CUR_DIR = Path(path).resolve()

def get_current_dir():
    global CUR_DIR
    return CUR_DIR

MANIFEST_PATH = None

def set_manifest_path(p: Union[str, Path]):
    global MANIFEST_PATH
    MANIFEST_FILE = Path(p)

def get_manifest_json(image_name: str)->Path:
    """ get last-build layer hashes info, 
    this file should be a json file with structure:
    {
        "layers": []
    }
    """
    global MANIFEST_PATH
    return MANIFEST_PATH or CUR_DIR.joinpath(f'{image_name}_layers.json')


def get_running_image_hashes(image_name: str) -> List[str]:
    """ check current image layer hash info """
    p = subprocess.run(split(f'docker inspect {image_name} -f {{{{.RootFS.Layers}}}}'),stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    if p.returncode !=0:
        raise RuntimeError(p.stderr.decode())
    return [ layer_hash.split(':')[1] for layer_hash in p.stdout.decode().replace('[', '').replace(']', '').split()]


def save_manifest_json(image_name:str):
    layer_hashes = get_running_image_hashes(image_name)
    manifest_path = get_manifest_json(image_name)
    with open(manifest_path, 'w') as f:
        json.dump({"layers": layer_hashes}, f)
    

def get_tar_path(image_name, category:Union[str, TarCategory]=TarCategory.BASE, compress:bool=False) -> Path:
    if isinstance(category, str):
        category = TarCategory(category)
    return CUR_DIR.resolve().joinpath(f'{image_name}_{category.value}.tar{".gz" if compress else ""}')

LOGGER_LEVEL = logging.INFO

def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(LOGGER_LEVEL)
    formatter = logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] [%(message)s]')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger


def set_log_level(level: int):
    global LOGGER_LEVEL
    LOGGER_LEVEL = level


def get_tarinfo(filename:str, contents: Optional[str]=None, encoding:str='utf8') -> Tuple[TarInfo, Optional[IO[bytes]]]:
    tarinfo = TarInfo(filename)
    contents_io = None
    if contents:
        raw_contents =  contents.encode(encoding=encoding)
        contents_io = BytesIO(raw_contents)
        tarinfo.size = len(raw_contents)
    elif Path(filename).is_file():
        contents_io = open(filename, 'rb')

    return tarinfo, contents_io


def run_process(cmd:str) -> CompletedProcess:
    """ use split if operator-system is not windows"""
    run_cmd = cmd if os.name == 'nt' else split(cmd)
    return subprocess.run(run_cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
