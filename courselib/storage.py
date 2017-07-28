import uuid
import os.path
from django.conf import settings
from hybrid_storage.storage import HybridStorage
from django.core.files.storage import FileSystemStorage


UploadedFileStorage = HybridStorage(
    location=settings.SUBMISSION_PATH + '/new',
    legacy_storage=FileSystemStorage(location=settings.SUBMISSION_PATH, base_url=None)
)


def upload_path(*path_components):
    """
    Builds an upload path that will be unique: upload_path(a, b, c, filename) -> a/b/c/uuid1/filename
    """
    filename = path_components[-1]
    path_components = list(path_components[:-1])
    uu = uuid.uuid1(uuid.getnode())
    components = path_components + [str(uu), filename.encode('ascii', 'ignore')]
    return os.path.join(*components)
