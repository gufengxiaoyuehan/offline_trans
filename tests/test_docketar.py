from offline_trans.util import get_manifest_json
import subprocess
from shlex import split
import os, tempfile
from . import get_docker_tar

# from ... import  create a new global variable and assign to import part
# like from a import b is equal:
#   import a
#   b = a.b
from offline_trans.docker_archive import DockerArchive

def test_tar_archive_v1_0():
    archive_v1_0 = get_docker_tar('docker_manifest', '1.0')
    assert DockerArchive.check_schema_version(archive_v1_0) == (1,0)

def test_tar_archive_v1_1():
    archive_v1_1 = get_docker_tar('docker_manifest','1.1')
    assert DockerArchive.check_schema_version(archive_v1_1) == (1, 1)

def test_tar_archive_v2_0():
    archive_v2_0 = get_docker_tar('docker_manifest','2.0')
    assert DockerArchive.check_schema_version(archive_v2_0) == (2, 0)


def test_docker_archive_get_layers_from_hash_v1_1():
    archive_v1_1 = get_docker_tar('docker_manifest','1.1')
    docker_archive = DockerArchive(archive_v1_1)
    layer_hash = docker_archive.layer_hashes[0]
    layer_paths = docker_archive.get_layer_from_hash(layer_hash)
    assert len(layer_paths) == 3, layer_paths
    assert layer_paths[0][1].endswith('layer.tar'), layer_paths
    assert layer_paths[0][1] in layer_paths[0][0], layer_paths