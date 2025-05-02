"""
AWS Storage System
The Right Honourable Reverend (trhr) 2020

ABOUT THIS PLUGIN:

This plugin migrates the Web-based portion of Evennia, namely images,
javascript, and other items located inside staticfiles into Amazon AWS (S3) for hosting.

Files hosted on S3 are "in the cloud," and while your personal
server may be sufficient for serving multimedia to a minimal number of users,
the perfect use case for this plugin would be:

1) Servers supporting heavy web-based traffic (webclient, etc)
2) With a sizable number of users
3) Where the users are globally distributed
4) Where multimedia files are served to users as a part of gameplay

Bottom line - if you're sending an image to a player every time they traverse a
map, the bandwidth reduction will be substantial. If not, probably skip
this one.

Note that storing and serving files via S3 is not technically free outside of
Amazon's "free tier" offering, which you may or may not be eligible for;
evennia's base install currently requires 1.5MB of storage space on S3,
making the current total cost to install this plugin ~$0.0005 per year. If
you have substantial media assets and intend to serve them to many users,
caveat emptor on a total cost of ownership - check AWS's pricing structure.

See the ./README.md file for details and install instructions.

"""

from django.core.exceptions import (
    ImproperlyConfigured,
    SuspiciousFileOperation,
    SuspiciousOperation,
)

try:
    from django.conf import settings as ev_settings

    if (
        not ev_settings.AWS_ACCESS_KEY_ID
        or not ev_settings.AWS_SECRET_ACCESS_KEY
        or not ev_settings.AWS_STORAGE_BUCKET_NAME
        or not ev_settings.AWS_S3_REGION_NAME
    ):
        raise ImproperlyConfigured(
            (
                "You must add AWS-specific settings"
                "to mygame/server/conf/secret_settings.py to use this plugin."
            )
        )

    if "mygame-evennia" == ev_settings.AWS_STORAGE_BUCKET_NAME:
        raise ImproperlyConfigured(
            (
                "You must customize your AWS_STORAGE_BUCKET_NAME"
                "in mygame/server/conf/secret_settings.py;"
                "it must be unique among ALL other S3 users"
            )
        )

except Exception as e:
    print(e)

import io
import mimetypes
import os
import posixpath
import threading
from gzip import GzipFile
from tempfile import SpooledTemporaryFile

from django.core.files.base import File
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible
from django.utils.encoding import filepath_to_uri, force_bytes, force_str, smart_str
from django.utils.timezone import is_naive, make_naive

try:
    from django.utils.six.moves.urllib import parse as urlparse
except ImportError:
    from urllib import parse as urlparse

try:
    import boto3.session
    from boto3 import __version__ as boto3_version
    from botocore.client import Config
    from botocore.exceptions import ClientError
except ImportError as e:
    raise ImproperlyConfigured("Couldn't load S3 bindings. %s Did you run 'pip install boto3?'" % e)

boto3_version_info = tuple([int(i) for i in boto3_version.split(".")])


def setting(name, default=None):
    """
    Helper function to get a Django setting by name. If setting doesn't exist
    it will return a default.

    Args:
        name (str): A Django setting name

    Returns:
        The value of the setting variable by that name

    """
    return getattr(ev_settings, name, default)


def safe_join(base, *paths):
    """
    Helper function, a version of django.utils._os.safe_join for S3 paths.
    Joins one or more path components to the base path component
    intelligently. Returns a normalized version of the final path.
    The final path must be located inside of the base path component
    (otherwise a ValueError is raised). Paths outside the base path
    indicate a possible security sensitive operation.

    Args:
        base (str): A path string to the base of the staticfiles
        *paths (list): A list of paths as referenced from the base path

    Returns:
        final_path (str): A joined path, base + filepath

    """
    base_path = force_str(base)
    base_path = base_path.rstrip("/")
    paths = [force_str(p) for p in paths]

    final_path = base_path + "/"
    for path in paths:
        _final_path = posixpath.normpath(posixpath.join(final_path, path))
        # posixpath.normpath() strips the trailing /. Add it back.
        if path.endswith("/") or _final_path + "/" == final_path:
            _final_path += "/"
        final_path = _final_path
    if final_path == base_path:
        final_path += "/"

    # Ensure final_path starts with base_path and that the next character after
    # the base path is /.
    base_path_len = len(base_path)
    if not final_path.startswith(base_path) or final_path[base_path_len] != "/":
        raise ValueError("the joined path is located outside of the base path" " component")

    return final_path.lstrip("/")


def check_location(storage):
    """
    Helper function to make sure that the storage location is configured correctly.

    Args:
        storage (Storage): A Storage object (Django)

    Raises:
        ImproperlyConfigured: If the storage location is not configured correctly,
            this is raised.

    """
    if storage.location.startswith("/"):
        correct = storage.location.lstrip("/")
        raise ImproperlyConfigured(
            "{}.location cannot begin with a leading slash. Found '{}'. Use '{}' instead.".format(
                storage.__class__.__name__,
                storage.location,
                correct,
            )
        )


def lookup_env(names):
    """
    Helper function for looking up names in env vars. Returns the first element found.

    Args:
        names (str): A list of environment variables

    Returns:
        value (str): The value of the found environment variable.

    """
    for name in names:
        value = os.environ.get(name)
        if value:
            return value


def get_available_overwrite_name(name, max_length):
    """
    Helper function indicating files that will be overwritten during trunc.

    Args:
        name (str): The name of the file
        max_length (int): The maximum length of a filename

    Returns:
        joined (path): A joined path including directory, file, and extension
    """
    if max_length is None or len(name) <= max_length:
        return name

    # Adapted from Django
    dir_name, file_name = os.path.split(name)
    file_root, file_ext = os.path.splitext(file_name)
    truncation = len(name) - max_length

    file_root = file_root[:-truncation]
    if not file_root:
        raise SuspiciousFileOperation(
            'aws-s3-cdn tried to truncate away entire filename "%s". '
            "Please make sure that the corresponding file field "
            'allows sufficient "max_length".' % name
        )
    return os.path.join(dir_name, "{}{}".format(file_root, file_ext))


@deconstructible
class S3Boto3StorageFile(File):
    """
    The default file object used by the S3Boto3Storage backend.
    This file implements file streaming using boto's multipart
    uploading functionality. The file can be opened in read or
    write mode.
    This class extends Django's File class. However, the contained
    data is only the data contained in the current buffer. So you
    should not access the contained file object directly. You should
    access the data via this class.
    Warning: This file *must* be closed using the close() method in
    order to properly write the file to S3. Be sure to close the file
    in your application.
    """

    buffer_size = setting("AWS_S3_FILE_BUFFER_SIZE", 5242880)

    def __init__(self, name, mode, storage, buffer_size=None):
        """
        Initializes the File object.

        Args:
            name (str): The name of the file
            mode (str): The access mode ('r' or 'w')
            storage (Storage): The Django Storage object
            buffer_size (int): The buffer size, for multipart uploads
        """
        if "r" in mode and "w" in mode:
            raise ValueError("Can't combine 'r' and 'w' in mode.")
        self._storage = storage
        self.name = name[len(self._storage.location) :].lstrip("/")
        self._mode = mode
        self._force_mode = (lambda b: b) if "b" in mode else force_str
        self.obj = storage.bucket.Object(storage._encode_name(name))
        if "w" not in mode:
            # Force early RAII-style exception if object does not exist
            self.obj.load()
        self._is_dirty = False
        self._raw_bytes_written = 0
        self._file = None
        self._multipart = None
        # 5 MB is the minimum part size (if there is more than one part).
        # Amazon allows up to 10,000 parts.  The default supports uploads
        # up to roughly 50 GB.  Increase the part size to accommodate
        # for files larger than this.
        if buffer_size is not None:
            self.buffer_size = buffer_size
        self._write_counter = 0

    @property
    def size(self):
        """
        Helper property to return filesize
        """
        return self.obj.content_length

    def _get_file(self):
        """
        Helper function to manage zipping and temporary files
        """
        if self._file is None:
            self._file = SpooledTemporaryFile(
                max_size=self._storage.max_memory_size,
                suffix=".S3Boto3StorageFile",
                dir=setting("FILE_UPLOAD_TEMP_DIR"),
            )
            if "r" in self._mode:
                self._is_dirty = False
                self.obj.download_fileobj(self._file)
                self._file.seek(0)
            if self._storage.gzip and self.obj.content_encoding == "gzip":
                self._file = GzipFile(mode=self._mode, fileobj=self._file, mtime=0.0)
        return self._file

    def _set_file(self, value):
        self._file = value

    file = property(_get_file, _set_file)

    def read(self, *args, **kwargs):
        """
        Checks if file is in read mode; then continues to boto3 operation
        """
        if "r" not in self._mode:
            raise AttributeError("File was not opened in read mode.")
        return self._force_mode(super().read(*args, **kwargs))

    def readline(self, *args, **kwargs):
        """
        Checks if file is in read mode; then continues to boto3 operation
        """
        if "r" not in self._mode:
            raise AttributeError("File was not opened in read mode.")
        return self._force_mode(super().readline(*args, **kwargs))

    def write(self, content):
        """
        Checks if file is in write mode or needs multipart handling,
        then continues to boto3 operation.
        """
        if "w" not in self._mode:
            raise AttributeError("File was not opened in write mode.")
        self._is_dirty = True
        if self._multipart is None:
            self._multipart = self.obj.initiate_multipart_upload(
                **self._storage._get_write_parameters(self.obj.key)
            )
        if self.buffer_size <= self._buffer_file_size:
            self._flush_write_buffer()
        bstr = force_bytes(content)
        self._raw_bytes_written += len(bstr)
        return super().write(bstr)

    @property
    def _buffer_file_size(self):
        pos = self.file.tell()
        self.file.seek(0, os.SEEK_END)
        length = self.file.tell()
        self.file.seek(pos)
        return length

    def _flush_write_buffer(self):
        """
        Flushes the write buffer.
        """
        if self._buffer_file_size:
            self._write_counter += 1
            self.file.seek(0)
            part = self._multipart.Part(self._write_counter)
            part.upload(Body=self.file.read())
            self.file.seek(0)
            self.file.truncate()

    def _create_empty_on_close(self):
        """
        Attempt to create an empty file for this key when this File is closed if no bytes
        have been written and no object already exists on S3 for this key.
        This behavior is meant to mimic the behavior of Django's builtin FileSystemStorage,
        where files are always created after they are opened in write mode:
            f = storage.open("file.txt", mode="w")
            f.close()

            Raises:
                Exception: Raised if a 404 error occurs
        """
        assert "w" in self._mode
        assert self._raw_bytes_written == 0

        try:
            # Check if the object exists on the server; if so, don't do anything
            self.obj.load()
        except ClientError as err:
            if err.response["ResponseMetadata"]["HTTPStatusCode"] == 404:
                self.obj.put(Body=b"", **self._storage._get_write_parameters(self.obj.key))
            else:
                raise

    def close(self):
        """
        Manages file closing after multipart uploads
        """
        if self._is_dirty:
            self._flush_write_buffer()
            parts = [
                {"ETag": part.e_tag, "PartNumber": part.part_number}
                for part in self._multipart.parts.all()
            ]
            self._multipart.complete(MultipartUpload={"Parts": parts})
        else:
            if self._multipart is not None:
                self._multipart.abort()
            if "w" in self._mode and self._raw_bytes_written == 0:
                self._create_empty_on_close()
        if self._file is not None:
            self._file.close()
            self._file = None


@deconstructible
class S3Boto3Storage(Storage):
    """
    Amazon Simple Storage Service using Boto3
    This storage backend supports opening files in read or write
    mode and supports streaming(buffering) data in chunks to S3
    when writing.
    """

    default_content_type = "application/octet-stream"
    # If config provided in init, signature_version and addressing_style settings/args are ignored.
    config = None
    # used for looking up the access and secret key from env vars
    access_key_names = ["AWS_S3_ACCESS_KEY_ID", "AWS_ACCESS_KEY_ID"]
    secret_key_names = ["AWS_S3_SECRET_ACCESS_KEY", "AWS_SECRET_ACCESS_KEY"]
    security_token_names = ["AWS_SESSION_TOKEN", "AWS_SECURITY_TOKEN"]
    security_token = None

    access_key = setting("AWS_S3_ACCESS_KEY_ID", setting("AWS_ACCESS_KEY_ID", ""))
    secret_key = setting("AWS_S3_SECRET_ACCESS_KEY", setting("AWS_SECRET_ACCESS_KEY", ""))
    file_overwrite = setting("AWS_S3_FILE_OVERWRITE", True)
    object_parameters = setting("AWS_S3_OBJECT_PARAMETERS", {})
    bucket_name = setting("AWS_STORAGE_BUCKET_NAME")
    auto_create_bucket = setting("AWS_AUTO_CREATE_BUCKET", False)
    default_acl = setting("AWS_DEFAULT_ACL", "public-read")
    bucket_acl = setting("AWS_BUCKET_ACL", default_acl)
    querystring_auth = setting("AWS_QUERYSTRING_AUTH", True)
    querystring_expire = setting("AWS_QUERYSTRING_EXPIRE", 3600)
    signature_version = setting("AWS_S3_SIGNATURE_VERSION")
    reduced_redundancy = setting("AWS_REDUCED_REDUNDANCY", False)
    location = setting("AWS_LOCATION", "")
    encryption = setting("AWS_S3_ENCRYPTION", False)
    custom_domain = setting("AWS_S3_CUSTOM_DOMAIN")
    addressing_style = setting("AWS_S3_ADDRESSING_STYLE")
    secure_urls = setting("AWS_S3_SECURE_URLS", True)
    file_name_charset = setting("AWS_S3_FILE_NAME_CHARSET", "utf-8")
    gzip = setting("AWS_IS_GZIPPED", False)
    preload_metadata = setting("AWS_PRELOAD_METADATA", False)
    gzip_content_types = setting(
        "GZIP_CONTENT_TYPES",
        (
            "text/css",
            "text/javascript",
            "application/javascript",
            "application/x-javascript",
            "image/svg+xml",
        ),
    )
    url_protocol = setting("AWS_S3_URL_PROTOCOL", "http:")
    endpoint_url = setting("AWS_S3_ENDPOINT_URL")
    proxies = setting("AWS_S3_PROXIES")
    region_name = setting("AWS_S3_REGION_NAME")
    use_ssl = setting("AWS_S3_USE_SSL", True)
    verify = setting("AWS_S3_VERIFY", None)
    max_memory_size = setting("AWS_S3_MAX_MEMORY_SIZE", 0)

    def __init__(self, acl=None, bucket=None, **settings):
        """
        Check if some of the settings we've provided as class attributes
        need to be overwritten with values passed in here.
        """
        for name, value in settings.items():
            if hasattr(self, name):
                setattr(self, name, value)

        check_location(self)

        # Backward-compatibility: given the anteriority of the SECURE_URL setting
        # we fall back to https if specified in order to avoid the construction
        # of unsecure urls.
        if self.secure_urls:
            self.url_protocol = "https:"

        self._entries = {}
        self._bucket = None
        self._connections = threading.local()

        self.access_key, self.secret_key = self._get_access_keys()
        self.security_token = self._get_security_token()

        if not self.config:
            kwargs = dict(
                s3={"addressing_style": self.addressing_style},
                signature_version=self.signature_version,
            )

            if boto3_version_info >= (1, 4, 4):
                kwargs["proxies"] = self.proxies
            self.config = Config(**kwargs)

    def __getstate__(self):
        state = self.__dict__.copy()
        state.pop("_connections", None)
        state.pop("_bucket", None)
        return state

    def __setstate__(self, state):
        state["_connections"] = threading.local()
        state["_bucket"] = None
        self.__dict__ = state

    @property
    def connection(self):
        """
        Creates the actual connection to S3
        """
        connection = getattr(self._connections, "connection", None)
        if connection is None:
            session = boto3.session.Session()
            self._connections.connection = session.resource(
                "s3",
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                aws_session_token=self.security_token,
                region_name=self.region_name,
                use_ssl=self.use_ssl,
                endpoint_url=self.endpoint_url,
                config=self.config,
                verify=self.verify,
            )
        return self._connections.connection

    @property
    def bucket(self):
        """
        Get the current bucket. If there is no current bucket object
        create it.
        """
        if self._bucket is None:
            self._bucket = self._get_or_create_bucket(self.bucket_name)
        return self._bucket

    @property
    def entries(self):
        """
        Get the locally cached files for the bucket.
        """
        if self.preload_metadata and not self._entries:
            self._entries = {
                self._decode_name(entry.key): entry
                for entry in self.bucket.objects.filter(Prefix=self.location)
            }
        return self._entries

    def _get_access_keys(self):
        """
        Gets the access keys to use when accessing S3. If none is
        provided in the settings then get them from the environment
        variables.
        """
        access_key = self.access_key or lookup_env(S3Boto3Storage.access_key_names)
        secret_key = self.secret_key or lookup_env(S3Boto3Storage.secret_key_names)
        return access_key, secret_key

    def _get_security_token(self):
        """
        Gets the security token to use when accessing S3. Get it from
        the environment variables.
        """
        security_token = self.security_token or lookup_env(S3Boto3Storage.security_token_names)
        return security_token

    def _get_or_create_bucket(self, name):
        """
        Retrieves a bucket if it exists, otherwise creates it.
        """
        bucket = self.connection.Bucket(name)
        if self.auto_create_bucket:
            try:
                # Directly call head_bucket instead of bucket.load() because head_bucket()
                # fails on wrong region, while bucket.load() does not.
                bucket.meta.client.head_bucket(Bucket=name)
            except ClientError as err:
                if err.response["ResponseMetadata"]["HTTPStatusCode"] == 301:
                    raise ImproperlyConfigured(
                        "Bucket %s exists, but in a different "
                        "region than we are connecting to. Set "
                        "the region to connect to by setting "
                        "AWS_S3_REGION_NAME to the correct region." % name
                    )

                elif err.response["ResponseMetadata"]["HTTPStatusCode"] == 404:
                    # Notes: When using the us-east-1 Standard endpoint, you can create
                    # buckets in other regions. The same is not true when hitting region specific
                    # endpoints. However, when you create the bucket not in the same region, the
                    # connection will fail all future requests to the Bucket after the creation
                    # (301 Moved Permanently).
                    #
                    # For simplicity, we enforce in S3Boto3Storage that any auto-created
                    # bucket must match the region that the connection is for.
                    #
                    # Also note that Amazon specifically disallows "us-east-1" when passing bucket
                    # region names; LocationConstraint *must* be blank to create in US Standard.

                    if self.bucket_acl:
                        bucket_params = {"ACL": self.bucket_acl}
                    else:
                        bucket_params = {}
                    region_name = self.connection.meta.client.meta.region_name
                    if region_name != "us-east-1":
                        bucket_params["CreateBucketConfiguration"] = {
                            "LocationConstraint": region_name
                        }
                    bucket.create(**bucket_params)
                else:
                    raise
        return bucket

    def _clean_name(self, name):
        """
        Cleans the name so that Windows style paths work
        """
        # Normalize Windows style paths
        clean_name = posixpath.normpath(name).replace("\\", "/")

        # os.path.normpath() can strip trailing slashes so we implement
        # a workaround here.
        if name.endswith("/") and not clean_name.endswith("/"):
            # Add a trailing slash as it was stripped.
            clean_name += "/"
        return clean_name

    def _normalize_name(self, name):
        """
        Normalizes the name so that paths like /path/to/ignored/../something.txt
        work. We check to make sure that the path pointed to is not outside
        the directory specified by the LOCATION setting.
        """
        try:
            return safe_join(self.location, name)
        except ValueError:
            raise SuspiciousOperation("Attempted access to '%s' denied." % name)

    def _encode_name(self, name):
        return smart_str(name, encoding=self.file_name_charset)

    def _decode_name(self, name):
        return force_str(name, encoding=self.file_name_charset)

    def _compress_content(self, content):
        """Gzip a given string content."""
        content.seek(0)
        zbuf = io.BytesIO()
        #  The GZIP header has a modification time attribute (see http://www.zlib.org/rfc-gzip.html)
        #  Each time a file is compressed it changes even if the other contents don't change
        #  For S3 this defeats detection of changes using MD5 sums on gzipped files
        #  Fixing the mtime at 0.0 at compression time avoids this problem
        zfile = GzipFile(mode="wb", fileobj=zbuf, mtime=0.0)
        try:
            zfile.write(force_bytes(content.read()))
        finally:
            zfile.close()
        zbuf.seek(0)
        # Boto 2 returned the InMemoryUploadedFile with the file pointer replaced,
        # but Boto 3 seems to have issues with that. No need for fp.name in Boto3
        # so just returning the BytesIO directly
        return zbuf

    def _open(self, name, mode="rb"):
        """
        Opens the file, if it exists.
        """
        name = self._normalize_name(self._clean_name(name))
        try:
            f = S3Boto3StorageFile(name, mode, self)
        except ClientError as err:
            if err.response["ResponseMetadata"]["HTTPStatusCode"] == 404:
                raise IOError("File does not exist: %s" % name)
            raise  # Let it bubble up if it was some other error
        return f

    def _save(self, name, content):
        """
        Stitches and cleans multipart uploads; normalizes file paths.
        """
        cleaned_name = self._clean_name(name)
        name = self._normalize_name(cleaned_name)
        params = self._get_write_parameters(name, content)

        if (
            self.gzip
            and params["ContentType"] in self.gzip_content_types
            and "ContentEncoding" not in params
        ):
            content = self._compress_content(content)
            params["ContentEncoding"] = "gzip"

        encoded_name = self._encode_name(name)
        obj = self.bucket.Object(encoded_name)
        if self.preload_metadata:
            self._entries[encoded_name] = obj

        content.seek(0, os.SEEK_SET)
        obj.upload_fileobj(content, ExtraArgs=params)
        return cleaned_name

    def delete(self, name):
        """
        Deletes a file from S3.
        """
        name = self._normalize_name(self._clean_name(name))
        self.bucket.Object(self._encode_name(name)).delete()

        if name in self._entries:
            del self._entries[name]

    def exists(self, name):
        """
        Checks if file exists.
        """
        name = self._normalize_name(self._clean_name(name))
        if self.entries:
            return name in self.entries
        try:
            self.connection.meta.client.head_object(Bucket=self.bucket_name, Key=name)
            return True
        except ClientError:
            return False

    def listdir(self, name):
        """
        Translational function to go from S3 file paths to the format
        Django's listdir expects.
        """
        path = self._normalize_name(self._clean_name(name))
        # The path needs to end with a slash, but if the root is empty, leave
        # it.
        if path and not path.endswith("/"):
            path += "/"

        directories = []
        files = []
        paginator = self.connection.meta.client.get_paginator("list_objects")
        pages = paginator.paginate(Bucket=self.bucket_name, Delimiter="/", Prefix=path)
        for page in pages:
            for entry in page.get("CommonPrefixes", ()):
                directories.append(posixpath.relpath(entry["Prefix"], path))
            for entry in page.get("Contents", ()):
                files.append(posixpath.relpath(entry["Key"], path))
        return directories, files

    def size(self, name):
        """
        Gets the filesize of a remote file.
        """
        name = self._normalize_name(self._clean_name(name))
        if self.entries:
            entry = self.entries.get(name)
            if entry:
                return entry.size if hasattr(entry, "size") else entry.content_length
            return 0
        return self.bucket.Object(self._encode_name(name)).content_length

    def _get_write_parameters(self, name, content=None):
        params = {}

        if self.encryption:
            params["ServerSideEncryption"] = "AES256"
        if self.reduced_redundancy:
            params["StorageClass"] = "REDUCED_REDUNDANCY"
        if self.default_acl:
            params["ACL"] = self.default_acl

        _type, encoding = mimetypes.guess_type(name)
        content_type = getattr(content, "content_type", None)
        content_type = content_type or _type or self.default_content_type

        params["ContentType"] = content_type
        if encoding:
            params["ContentEncoding"] = encoding

        params.update(self.get_object_parameters(name))
        return params

    def get_object_parameters(self, name):
        """
        Returns a dictionary that is passed to file upload. Override this
        method to adjust this on a per-object basis to set e.g ContentDisposition.
        By default, returns the value of AWS_S3_OBJECT_PARAMETERS.
        Setting ContentEncoding will prevent objects from being automatically gzipped.
        """
        return self.object_parameters.copy()

    def get_modified_time(self, name):
        """
        Returns an (aware) datetime object containing the last modified time if
        USE_TZ is True, otherwise returns a naive datetime in the local timezone.
        """
        name = self._normalize_name(self._clean_name(name))
        entry = self.entries.get(name)
        # only call self.bucket.Object() if the key is not found
        # in the preloaded metadata.
        if entry is None:
            entry = self.bucket.Object(self._encode_name(name))
        if setting("USE_TZ"):
            # boto3 returns TZ aware timestamps
            return entry.last_modified
        else:
            return make_naive(entry.last_modified)

    def modified_time(self, name):
        """Returns a naive datetime object containing the last modified time.
        If USE_TZ=False then get_modified_time will return a naive datetime
        so we just return that, else we have to localize and strip the tz
        """
        mtime = self.get_modified_time(name)
        return mtime if is_naive(mtime) else make_naive(mtime)

    def _strip_signing_parameters(self, url):
        """
        Boto3 does not currently support generating URLs that are unsigned. Instead we
        take the signed URLs and strip any querystring params related to signing and expiration.
        Note that this may end up with URLs that are still invalid, especially if params are
        passed in that only work with signed URLs, e.g. response header params.
        The code attempts to strip all query parameters that match names of known parameters
        from v2 and v4 signatures, regardless of the actual signature version used.
        """
        split_url = urlparse.urlsplit(url)
        qs = urlparse.parse_qsl(split_url.query, keep_blank_values=True)
        blacklist = {
            "x-amz-algorithm",
            "x-amz-credential",
            "x-amz-date",
            "x-amz-expires",
            "x-amz-signedheaders",
            "x-amz-signature",
            "x-amz-security-token",
            "awsaccesskeyid",
            "expires",
            "signature",
        }
        filtered_qs = ((key, val) for key, val in qs if key.lower() not in blacklist)
        # Note: Parameters that did not have a value in the original query string will have
        # an '=' sign appended to it, e.g ?foo&bar becomes ?foo=&bar=
        joined_qs = ("=".join(keyval) for keyval in filtered_qs)
        split_url = split_url._replace(query="&".join(joined_qs))
        return split_url.geturl()

    def url(self, name, parameters=None, expire=None):
        """
        Returns the URL of a remotely-hosted file
        """
        # Preserve the trailing slash after normalizing the path.
        name = self._normalize_name(self._clean_name(name))
        if self.custom_domain:
            return "{}//{}/{}".format(self.url_protocol, self.custom_domain, filepath_to_uri(name))
        if expire is None:
            expire = self.querystring_expire

        params = parameters.copy() if parameters else {}
        params["Bucket"] = self.bucket.name
        params["Key"] = self._encode_name(name)
        url = self.bucket.meta.client.generate_presigned_url(
            "get_object", Params=params, ExpiresIn=expire
        )
        if self.querystring_auth:
            return url
        return self._strip_signing_parameters(url)

    def get_available_name(self, name, max_length=None):
        """Overwrite existing file with the same name."""
        name = self._clean_name(name)
        if self.file_overwrite:
            return get_available_overwrite_name(name, max_length)
        return super().get_available_name(name, max_length)
