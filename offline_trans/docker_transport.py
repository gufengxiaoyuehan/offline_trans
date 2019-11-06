"""use a hash json file and new saved archive image to check  layers should to keep
or to remove if the bases
"""
import json
import os
import tempfile
from pathlib import Path
from tarfile import open as tar_open
from typing import List, Optional, Tuple, Union

from offline_trans.exceptions import DockerArchiveNotFound

from .docker_archive import DockerArchive, DockerManifest
from .util import (TarCategory, get_logger, get_manifest_json,
                   get_running_image_hashes, get_tar_path, get_tarinfo,
                   run_process, set_current_dir)

logger = get_logger(__name__)

def pre_check(base_layer_hashes: List[str], curre_layer_hashes: List[str]) -> Tuple[int, Optional[str], set]:
    """check if all requirements statisfied
    if str returned, prompt it to user as a remind
    return layers that not need to trans"""
    # no different found
    if not (set(curre_layer_hashes) - set(base_layer_hashes) or set(base_layer_hashes) - set(curre_layer_hashes)):
        return 1,f'no different layers', set()
    elif not (set(base_layer_hashes) & set(curre_layer_hashes)):
        return 2,f'no same layers', set(curre_layer_hashes)
    # keep the same
    return 0,"", set(base_layer_hashes) & set(curre_layer_hashes)


def export_docker_diff(image_name: str, output_dir: str="") -> Union[str, Path]:
    """export docker layers to output file path"""
    if output_dir:
        set_current_dir(output_dir)

    manifest_path = get_manifest_json(image_name) 
    logger.info(f"manifest path {manifest_path}")
    if not manifest_path.exists():
        raise DockerArchiveNotFound(f'base manifest {manifest_path} not found')
    base_manifest = DockerManifest(manifest_path)
    current_layer_hashes = get_running_image_hashes(image_name)

    status, reason, keeped_set = pre_check(base_manifest.layer_hashes, current_layer_hashes)
    logger.debug(f'keeped layer hashes {keeped_set}')
    if status == 2:
        # export all to tar.gz
        image_path : Path = get_tar_path(image_name, TarCategory.DIFF)
        logger.info(f'{reason}, save all to {image_path}')
        p = run_process(f'docker save -o {image_path} {image_name}')
        if p.returncode != 0:
            raise RuntimeError(p.stderr)
        with tar_open(image_path.with_suffix('.tar.gz'), 'w:gz') as tar_out, tar_open(image_path) as tar_inpt:
            tar_out.addfile(*get_tarinfo('keeped.json', json.dumps(list(keeped_set))))
            for member in tar_inpt.getmembers():
                tar_out.addfile(member, tar_inpt.extractfile(member))
        os.unlink(image_path)
        image_path = image_path.with_suffix('.tar.gz') 

    elif status == 1:
        image_path = get_tar_path(image_name, TarCategory.DIFF, True)
        logger.info(f'{reason}, save stub to {image_path}')
        with tar_open(image_path, 'w:gz') as tar_file:
            tar_file.addfile(* get_tarinfo('keeped.json', json.dumps(list(keeped_set))))
    else:
        temp_tar_file = tempfile.mktemp()
        p = run_process(f'docker save -o {temp_tar_file} {image_name}')
        if p.returncode != 0:
            raise RuntimeError(p.stderr)
        
        new_docker_archive = DockerArchive(temp_tar_file)
        diff_layer_hash = set(new_docker_archive.layer_hashes) - keeped_set
        
        diff_layer_paths = new_docker_archive.get_layers_from_hashes(diff_layer_hash)

        image_path = get_tar_path(image_name, TarCategory.DIFF, True)
        logger.debug(f'save to {image_path}')
        with tar_open(image_path, 'w:gz') as diff_tar:
            for diff_layer_files in diff_layer_paths:
                for layer_path, arcname in diff_layer_files:
                    diff_tar.add(layer_path, arcname=arcname)
            
            for meta_file, arcname in new_docker_archive.meta_files:
                diff_tar.add(meta_file, arcname)

            diff_tar.addfile(*get_tarinfo('keeped.json', json.dumps(list(keeped_set))))
        os.unlink(temp_tar_file)
    return image_path
      

def import_docker_diff(image_name:str, input_dir: Optional[str]=None) -> Union[Path,str]:
    """ update docker images with supplied layers """
    if input_dir:
        set_current_dir(input_dir)

    diff_image_path = get_tar_path(image_name, 'diff', True)
    if not diff_image_path.exists():
        raise RuntimeError(f'no file find : {diff_image_path}')
    base_manifest = get_manifest_json(image_name)
    base_manifest_archive = DockerManifest(base_manifest)
    if not base_manifest.exists():
        raise RuntimeError(f'base mainfest not find: {base_manifest}')
    curr_layer_hashes = get_running_image_hashes(image_name)
    res,reason, keeped_set = pre_check(base_manifest_archive.layer_hashes, curr_layer_hashes)
    if res !=1:
        raise RuntimeError(f'current running is not equal to base manifest which \
            used to extract diff layers\nbase:\t{base_manifest_archive.layer_hashes}\n\
            current running:\t {curr_layer_hashes}')

    base_fd, base_image_path = tempfile.mkstemp(suffix='')
    p = run_process(f'docker save -o {base_image_path} {image_name}')
    if p.returncode !=0:
        raise RuntimeError(p.stderr)
    temp_fd, temp_image_path = tempfile.mkstemp(suffix='')
    os.close(base_fd), os.close(temp_fd)

    base_image_archive = DockerArchive(base_image_path)
    
    with tar_open(diff_image_path) as diff_image_tar, tar_open(temp_image_path, 'w') as temp_image_tar:
        # rm meta info
        for member in diff_image_tar:
            if member.name != 'keeped.json':
                temp_image_tar.addfile(member, diff_image_tar.extractfile(member))
        keeped_file = diff_image_tar.extractfile('keeped.json')

        if keeped_file:
            keeped_layers = json.load(keeped_file)

            for layer_hash in keeped_layers:
                for file_path, arcname in base_image_archive.get_layer_from_hash(layer_hash) :
                    temp_image_tar.add(file_path, arcname)

    logger.info(f'build tar file at {temp_image_path}')
    return temp_image_path
