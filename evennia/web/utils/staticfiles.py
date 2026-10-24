"""
Storage backend for the static files (CSS, JS, images etc) used by the website and webclient.

This is set up by the `STORAGES["staticfiles"]` setting.

"""

import os

from django.contrib.staticfiles.storage import ManifestStaticFilesStorage


class CacheBustingStaticFilesStorage(ManifestStaticFilesStorage):
    """
    Static files storage that 'cache-busts' static files.

    When `collectstatic` runs (Evennia does this every time the server is started or
    reloaded from the command line), a copy of each static file is stored with a hash of
    its contents in its name, like `webclient.css` -> `webclient.3a7bd3e2360a.css`.
    The `{% static %}` template tag then points to the hashed copy. Since the name
    changes whenever the contents change, browsers will download the new version instead
    of re-using an outdated copy from their cache. References to other static files
    inside CSS files (like `url(...)`) are updated to point to the hashed copies too.

    This differs from Django's `ManifestStaticFilesStorage` in that:

    - Hashed urls are used also when `DEBUG` is set. Evennia always serves the collected
      files in `STATIC_ROOT`, so the hashed copies are always available.
    - A file not found in the manifest (such as a file added after the last
      `collectstatic`) gets its normal, un-hashed url instead of raising an error.
    - A reference to a file that can't be found inside a CSS or JS file is left as-is
      instead of making `collectstatic` (and thus server startup) fail.
    - The manifest is re-read when it changes on disk, so running `collectstatic` takes
      effect without having to reload the server.

    """

    def _get_manifest_stamp(self):
        """
        Get a stamp identifying the current version of the manifest file on disk.

        Returns:
            tuple or None: The manifest file's `(mtime_ns, size)`, or `None` if it
                could not be found.

        """
        try:
            stat = os.stat(self.manifest_storage.path(self.manifest_name))
        except (OSError, NotImplementedError):
            return None
        return (stat.st_mtime_ns, stat.st_size)

    def load_manifest(self):
        """
        Load the manifest, remembering which version of the file was loaded.

        Returns:
            tuple: `(hashed_files, manifest_hash)`, where `hashed_files` maps original
                names to hashed names.

        Raises:
            ValueError: If the manifest could not be parsed.

        """
        self._manifest_stamp = self._get_manifest_stamp()
        return super().load_manifest()

    def _refresh_manifest(self):
        """
        Re-read the manifest if it changed on disk since it was last loaded.

        """
        if self._get_manifest_stamp() == self._manifest_stamp:
            return
        try:
            self.hashed_files, self.manifest_hash = self.load_manifest()
        except ValueError:
            # most likely collectstatic is writing the manifest right now; keep using
            # the old one and try again next time
            self._manifest_stamp = None

    def stored_name(self, name):
        """
        Get the hashed name of a static file, as stored in the manifest.

        Args:
            name (str): The static file's path, relative to `STATIC_ROOT`.

        Returns:
            str: The hashed name, or `name` unchanged if the file is not in the manifest.

        """
        try:
            return super().stored_name(name)
        except ValueError:
            return name

    def url(self, name, force=False):
        """
        Get the url to a static file, pointing to its hashed copy if there is one.

        Args:
            name (str): The static file's path, relative to `STATIC_ROOT`.
            force (bool, optional): Unused; hashed urls are always returned, also when
                `DEBUG` is set.

        Returns:
            str: The url to the file.

        """
        self._refresh_manifest()
        return self._url(self.stored_name, name, force=True)

    def url_converter(self, name, hashed_files, template=None):
        """
        Get the function used to replace references to other static files inside a
        CSS or JS file with their hashed names.

        Args:
            name (str): The name of the file being processed.
            hashed_files (dict): The files hashed so far, mapping original to hashed names.
            template (str, optional): Template for the replacement string.

        Returns:
            callable: A function taking a regex match and returning the replacement string.
                References to files that can't be found are left unchanged.

        """
        converter = super().url_converter(name, hashed_files, template=template)

        def _converter(matchobj):
            try:
                return converter(matchobj)
            except ValueError:
                return matchobj["matched"]

        return _converter
