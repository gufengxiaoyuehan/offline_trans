class DockerArchiveBaseException(Exception):
    """base exception class"""


class DockerArchiveNotFound(DockerArchiveBaseException):
    """docker tar not found"""


class FaultDockerManifest(DockerArchiveBaseException):
    """ not a avaliable docker manifest """


class DockerSchemaNotSupport(DockerArchiveBaseException):
    """ not support schema version """
