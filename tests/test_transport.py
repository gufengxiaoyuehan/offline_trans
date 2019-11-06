import shutil
from tarfile import is_tarfile, open as tar_open
from offline_trans.util import get_manifest_json
from offline_trans.docker_archive import DockerArchive, DockerManifest
import json, os
from nose import with_setup, tools
from offline_trans.docker_transport import get_running_image_hashes, export_docker_diff, import_docker_diff, pre_check
from offline_trans.util import get_tar_path
from . import get_docker_tar,base_path

def test_get_running_image_hashes():
    assert get_running_image_hashes('hello-world') == ['af0b15c8625bb1938f1d7b17081031f649fd14e6b233688eea3c5483994a66a3']


def test_export_docker_diff():
    image_name = 'hello-world'
    

def test_pre_check_return_2():
    image_name = 'hello-world'
    
    manifest_path = get_manifest_json(image_name) 
    current_layer_hashes = get_running_image_hashes(image_name)
    base_layer_manifest = DockerManifest(manifest_path)
    res = pre_check(base_layer_manifest.layer_hashes, current_layer_hashes)
    assert res[0] == 2, res[0]
    assert res[2] == set(['af0b15c8625bb1938f1d7b17081031f649fd14e6b233688eea3c5483994a66a3']), res[2]

def test_pre_check_return_1():
    # TODO check v1 and v2
    base_file = get_docker_tar('offline_trans', '1')
    base_archive = DockerArchive(base_file)
    curr_file = get_docker_tar('offline_trans', '2')
    curr_archive = DockerArchive(curr_file)
    res = pre_check(base_archive.layer_hashes, curr_archive.layer_hashes)
    assert res[0] == 1
    assert res[2] == set(curr_archive.layer_hashes) - set(base_archive.layer_hashes)


def test_docker_trans_export_with_diff():
    res_dif = get_tar_path('offline_trans', 'diff', True)
    export_docker_diff('offline_trans')
    assert res_dif.exists(), res_dif
    assert is_tarfile(res_dif), res_dif
    with tar_open(res_dif) as tar:
        keeped = json.load(tar.extractfile('keeped.json'))
        assert len(keeped) == 2


def import_error_setup():
    base_hash_path = base_path.joinpath('offline_trans_layers.json')
    base_same_hash_path = base_path.joinpath('offline_trans_same_layers.json')
    tmp =base_hash_path.with_suffix('.tmp.json')  
    shutil.copy(base_hash_path, tmp)
    shutil.copy(base_same_hash_path, base_hash_path)

def import_error_tear_down():
    base_hash_path = base_path.joinpath('offline_trans_layers.json')
    base_same_hash_path = base_path.joinpath('offline_trans_same_layers.json')
    tmp =base_hash_path.with_suffix('.tmp.json')  
    shutil.copy(base_hash_path, base_same_hash_path)
    shutil.copy(tmp, base_hash_path)
    os.unlink(tmp)

@with_setup(import_error_setup, import_error_tear_down)
@tools.raises(RuntimeError)
def test_docker_trans_import_with_diff_raise_error():
    import_docker_diff('offline_trans')

def import_docker_diff_setup():
    ...

def import_docker_diff_tear_down():
    ...

@with_setup(import_docker_diff_setup, import_docker_diff_tear_down)
def test_docker_trans_import_with_diff():
    import_docker_diff('offline_trans')