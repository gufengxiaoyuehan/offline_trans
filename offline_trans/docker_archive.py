"""
docker tarfile use different schmea version. detail see
current there two main version used in docker commands:
docker save/load : version 1
docker pull/push : version 2
"""
import abc
from abc import abstractmethod
import shutil
from os import PathLike
import os
from os.path import exists
from sys import version
import tarfile
import pathlib
import json
import tempfile
from typing import IO, Iterable, List, Optional, Union, Tuple, Iterator

from pathlib import Path

from .exceptions import DockerArchiveNotFound, FaultDockerManifest, DockerSchemaNotSupport

# see https://github.com/moby/moby/tree/master/image/spec for details
# noly repository file -- version 1
# manifest.json and configure.json and manifest.json is a list --  version 1.1 and above
# only manifest.json and container version key 2 -- version 2
REPOSITORY_FILE="repositories"
MANIFEST_FILE='manifest.json'
CONFIG_FILE="*.json"


class DockerArchive(abc.ABC):
    """docker tar contains all the changeset and related inforamtion
    for running.
    """
    def __new__(cls, tar_file: Union[str, Path], *args, **kwargs) -> 'DockerArchive':
        """
        """
        version = DockerArchive.check_schema_version(str(tar_file))
        if version == (1, 0):
            obj = super().__new__(DockerArchiveVersion1_0)
            obj.__version = (1,0)
        elif version == (1, 1):
            obj = super().__new__(DockerArchiveVersion1_1)
            obj.__version = (1,1)
        elif version == (2, 0):
            obj = super().__new__(DockerArchiveVersion2_0)
            obj.__version = (2,0)
        else:
            raise DockerSchemaNotSupport(f'version {version} of {tar_file} not support currently')
        return obj
    
    def __init__(self, tar_file: Union[str, Path], *args, **kwargs):
        """convert tarfile to a directory"""
        if tarfile.is_tarfile(str(tar_file)):
            __archive = tempfile.mkdtemp()
            with tarfile.open(tar_file) as tar:
                tar.extractall(__archive)
        else:
            __archive = tar_file
        self._archive = Path(__archive)

    @abc.abstractproperty
    def meta_files(self) -> Tuple[str, str]:
        """meta file path"""

    @abc.abstractproperty
    def layer_hashes(self) -> List[str]:
        """get content-address hash ids of all layers
        """

    @abc.abstractmethod
    def get_layer_from_hash(self, layer_hash:str) -> Tuple[Tuple[str, str], ...]:
        """get layer name and optional legacy affix files: like layer json and VERSION
        and relative name"""

    def get_layers_from_hashes(self, hashes: Iterable[str]) -> List[Tuple[Tuple[str,str],...]]:
        return [self.get_layer_from_hash(layer_hash) for layer_hash in hashes]

    @staticmethod
    def check_schema_version(tar_file: Union[str, Path]) -> Tuple[int,int]:
        """
        get the schema version
        """
        if isinstance(tar_file, str):
            docker_tar = Path(tar_file)
        else:
            docker_tar = tar_file
        
        
        if docker_tar.is_dir():
            return DockerArchive._check_dir_schema(docker_tar)
        elif docker_tar.is_file():
            return DockerArchive._check_tarfile_schema(docker_tar)
        else:
            raise DockerArchiveNotFound(f"{tar_file} is not a legal docker archive path")
            

    @staticmethod
    def _check_dir_schema(tar_dir: Path)-> Tuple[int, int]:
        """get schema version if this is a directory"""
        repositry_path = tar_dir.joinpath(REPOSITORY_FILE)
        manifest_path = tar_dir.joinpath(MANIFEST_FILE)

        if not manifest_path.exists() and repositry_path.exists():
            return (1,0)
        elif manifest_path.exists():
            manifest = json.load(open(manifest_path))
            if isinstance(manifest, list) and tar_dir.joinpath(manifest[0]['Config']):
                return (1,1)
            elif isinstance(manifest, dict) and manifest.get('schemaVersion') == 2:
                return (2,0)
            else:
                raise FaultDockerManifest(f"necessary config file not found in {tar_dir}")
        else:
            raise FaultDockerManifest(f"necessary config file not found in {tar_dir}")
        
    @staticmethod
    def _check_tarfile_schema(tar_file: Path) -> Tuple[int, int]:
        """ get schema version from tar file """
        tar_filepath = str(tar_file.resolve())
        if tarfile.is_tarfile(tar_filepath):
            with tarfile.open(tar_file) as docker_tar, tempfile.TemporaryDirectory() as tmp_tar_dir:
                docker_tar.extractall(tmp_tar_dir)
                return DockerArchive._check_dir_schema(Path(tmp_tar_dir))
        else:
            raise FaultDockerManifest(f"{tar_file} is not a tarfile")

    def __del__(self):
        shutil.rmtree(self._archive)


class DockerArchiveVersion1_0(DockerArchive):
    ...


class DockerArchiveVersion1_1(DockerArchive):
    def __init__(self, tarfile):
        super().__init__(tarfile)

        self._manifest = None
        self._config = None
        self.__config_file = None

    @property
    def meta_files(self) -> Tuple[Tuple[str, str], ...]:
        return (
            (str(self._archive.joinpath('manifest.json')), 'manifest.json'),
            (str(self._archive.joinpath('repositories')), 'repositories'), 
            (str(self._archive.joinpath(self.config_file)), self.__config_file),
        )
    @property
    def config_file(self) -> str:
        if not self.__config_file:
            self.__config_file = self.manifest['Config']
        return self.__config_file

    @property
    def layer_hashes(self) -> List[str]:
        return [ layer_hash.split(':')[1] for layer_hash in self.configure['rootfs']['diff_ids']]

    @property
    def manifest(self) -> dict:
        if not self._manifest:
            self._manifest = json.load(open(self._archive.joinpath('manifest.json')))[0]
        return self._manifest

    @property
    def configure(self) -> dict:
        if not self._config:
            self.__config_file = self.manifest['Config']
            self._config =json.load(open(self._archive.joinpath(self.__config_file))) 
        return self._config

    def get_layer_from_hash(self, layer_hash)-> Tuple[Tuple[str, str], ...]:
        layer_names = self.manifest['Layers']
        layer_hashes = self.layer_hashes
        layers = dict(zip(layer_hashes, layer_names))
        layer_name = Path(layers[layer_hash])
        abs_layer_name = self._archive.joinpath(layer_name)
        return ((str(abs_layer_name), str(layer_name)), (str(abs_layer_name.with_name('VERSION')), 
        str(layer_name.with_name('VERSION'))), (str(abs_layer_name.with_name('json')), str(layer_name.with_name('json'))))
    
    
class DockerArchiveVersion2_0(DockerArchive):
    ...


class DockerManifest:
    """json file contains informations about compared layer's hash info
    json file structure:
    {
        layers: []
    }
    """
    def __init__(self, manifest_file:Union[str, PathLike]):
        self.__manifest = json.load(open(manifest_file))

        self.__layer_hashes = None

    @property
    def layer_hashes(self) -> List[str]:
        """get all layer's hash info"""
        if not self.__layer_hashes:
            self.__layer_hashes = self.__manifest.get('layers')
        return self.__layer_hashes

    