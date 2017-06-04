
""" pydpkg: tools for inspecting dpkg archive files in python
            without any dependency on libapt
"""

from __future__ import absolute_import

# stdlib imports
import io
import logging
import os
import tarfile
from gzip import GzipFile
from hashlib import md5, sha1, sha256
from email import message_from_string as Message

# pypi imports
import six
from arpy import Archive

REQUIRED_HEADERS = ('package', 'version', 'architecture')

logging.basicConfig()


class DpkgError(Exception):

    """Base error class for pydpkg"""
    pass


class DpkgVersionError(Exception):

    """Corrupt or unparseable version string"""
    pass


class DpkgMissingControlFile(DpkgError):

    """No control file found in control.tar.gz"""
    pass


class DpkgMissingControlGzipFile(DpkgError):

    """No control.tar.gz file found in dpkg file"""
    pass


class DpkgMissingRequiredHeaderError(DpkgError):

    """Corrupt package missing a required header"""
    pass


class Dpkg(object):

    """Class allowing import and manipulation of a debian package file."""

    def __init__(self, filename=None, ignore_missing=False, logger=None):
        self.filename = os.path.expanduser(filename)
        self.ignore_missing = ignore_missing
        if not isinstance(self.filename, six.string_types):
            raise DpkgError('filename argument must be a string')
        if not os.path.isfile(self.filename):
            raise DpkgError('filename "%s" does not exist', filename)
        self._log = logger or logging.getLogger(__name__)
        self._fileinfo = None
        self._control_str = None
        self._headers = None
        self._message = None

    def __repr__(self):
        return repr(self.control_str)

    def __str__(self):
        return six.text_type(self.control_str)

    @property
    def message(self):
        """Return an email.Message object containing the package control
        structure."""
        if not self._message:
            self._message = self._process_dpkg_file(self.filename)
        return self._message

    @property
    def control_str(self):
        """Return the control message as a string"""
        if not self._control_str:
            self._control_str = self.message.as_string()
        return self._control_str

    @property
    def headers(self):
        """Return the control message headers as a dict"""
        if not self._headers:
            self._headers = dict(self.message.items())
        return self._headers

    @property
    def fileinfo(self):
        """Return a dictionary containing md5/sha1/sha256 checksums
        and the size in bytes of our target file."""
        if not self._fileinfo:
            h_md5 = md5()
            h_sha1 = sha1()
            h_sha256 = sha256()
            with open(self.filename, 'rb') as dpkg_file:
                for chunk in iter(lambda: dpkg_file.read(128), b''):
                    h_md5.update(chunk)
                    h_sha1.update(chunk)
                    h_sha256.update(chunk)
            self._fileinfo = {
                'md5':      h_md5.hexdigest(),
                'sha1':     h_sha1.hexdigest(),
                'sha256':   h_sha256.hexdigest(),
                'filesize': os.path.getsize(self.filename)
            }
        return self._fileinfo

    @property
    def md5(self):
        """Return the md5 hash of our target file"""
        return self.fileinfo['md5']

    @property
    def sha1(self):
        """Return the sha1 hash of our target file"""
        return self.fileinfo['sha1']

    @property
    def sha256(self):
        """Return the sha256 hash of our target file"""
        return self.fileinfo['sha256']

    @property
    def filesize(self):
        """Return the size of our target file"""
        return self.fileinfo['filesize']

    def get_header(self, header):
        """ case-independent query for a control message header value """
        return self.headers.get(header.lower(), '')

    def compare_version_with(self, version_str):
        """Compare my version to an arbitrary version"""
        return Dpkg.compare_versions(self.get_header('version'), version_str)

    @staticmethod
    def _force_encoding(obj, encoding='utf-8'):
        """Enforce uniform text encoding"""
        if isinstance(obj, six.string_types):
            if not isinstance(obj, six.text_type):
                obj = six.text_type(obj, encoding)
        return obj

    def _process_dpkg_file(self, filename):
        dpkg_archive = Archive(filename)
        dpkg_archive.read_all_headers()
        try:
            control_tgz = dpkg_archive.archived_files[b'control.tar.gz']
        except KeyError:
            raise DpkgMissingControlGzipFile(
                'Corrupt dpkg file: no control.tar.gz file in ar archive.')
        self._log.debug('found controlgz: %s', control_tgz)

        # have to pass through BytesIO because gzipfile doesn't support seek
        # from end; luckily control tars are tiny
        with GzipFile(fileobj=control_tgz) as gzf:
            self._log.debug('opened gzip file: %s', gzf)
            with tarfile.open(fileobj=io.BytesIO(gzf.read())) as control_tar:
                self._log.debug('opened tar file: %s', control_tar)
                # pathname in the tar could be ./control, or just control
                # (there would never be two control files...right?)
                tar_members = [
                    os.path.basename(x.name) for x in control_tar.getmembers()]
                self._log.debug('got tar members: %s', tar_members)
                if 'control' not in tar_members:
                    raise DpkgMissingControlFile(
                        'Corrupt dpkg file: no control file in control.tar.gz')
                control_idx = tar_members.index('control')
                self._log.debug('got control index: %s', control_idx)
                # at last!
                control_file = control_tar.extractfile(
                    control_tar.getmembers()[control_idx])
                self._log.debug('got control file: %s', control_file)
                message_body = control_file.read()
                # py27 lacks email.message_from_bytes, so...
                if isinstance(message_body, bytes):
                    message_body = message_body.decode('utf-8')
                message = Message(message_body)
                self._log.debug('got control message: %s', message)

        for req in REQUIRED_HEADERS:
            if req not in list(map(str.lower, message.keys())):
                import pdb
                pdb.set_trace()
                if self.ignore_missing:
                    self._log.debug(
                        'Header "%s" not found in control message', req)
                    continue
                raise DpkgMissingRequiredHeaderError(
                    'Corrupt control section; header: "%s" not found' % req)
        self._log.debug('all required headers found')

        for header in message.keys():
            self._log.debug('coercing header to utf8: %s', header)
            message.replace_header(
                header, self._force_encoding(message[header]))
        self._log.debug('all required headers coerced')

        return message

    @staticmethod
    def get_epoch(version_str):
        """ Parse the epoch out of a package version string.
        Return (epoch, version); epoch is zero if not found."""
        try:
            # there could be more than one colon,
            # but we only care about the first
            e_index = version_str.index(':')
        except ValueError:
            # no colons means no epoch; that's valid, man
            return 0, version_str

        try:
            epoch = int(version_str[0:e_index])
        except ValueError:
            raise DpkgVersionError(
                'Corrupt dpkg version %s: epochs can only be ints, and '
                'epochless versions cannot use the colon character.' %
                version_str)

        return epoch, version_str[e_index + 1:]

    @staticmethod
    def get_upstream(version_str):
        """Given a version string that could potentially contain both an upstream
        revision and a debian revision, return a tuple of both.  If there is no
        debian revision, return 0 as the second tuple element."""
        try:
            d_index = version_str.rindex('-')
        except ValueError:
            # no hyphens means no debian version, also valid.
            return version_str, '0'

        return version_str[0:d_index], version_str[d_index+1:]

    @staticmethod
    def split_full_version(version_str):
        """Split a full version string into epoch, upstream version and
        debian revision.
        :param: version_str
        :returns: tuple """
        epoch, full_ver = Dpkg.get_epoch(version_str)
        upstream_rev, debian_rev = Dpkg.get_upstream(full_ver)
        return epoch, upstream_rev, debian_rev

    @staticmethod
    def get_alphas(revision_str):
        """Return a tuple of the first non-digit characters of a revision (which
        may be empty) and the remaining characters."""
        # get the index of the first digit
        for i, char in enumerate(revision_str):
            if char.isdigit():
                if i == 0:
                    return '', revision_str
                return revision_str[0:i], revision_str[i:]
        # string is entirely alphas
        return revision_str, ''

    @staticmethod
    def get_digits(revision_str):
        """Return a tuple of the first integer characters of a revision (which
        may be empty) and the remains."""
        # If the string is empty, return (0,'')
        if not revision_str:
            return 0, ''
        # get the index of the first non-digit
        for i, char in enumerate(revision_str):
            if not char.isdigit():
                if i == 0:
                    return 0, revision_str
                return int(revision_str[0:i]), revision_str[i:]
        # string is entirely digits
        return int(revision_str), ''

    @staticmethod
    def listify(revision_str):
        """Split a revision string into a list of alternating between strings and
        numbers, padded on either end to always be "str, int, str, int..." and
        always be of even length.  This allows us to trivially implement the
        comparison algorithm described at
        http://debian.org/doc/debian-policy/ch-controlfields.html#s-f-Version
        """
        result = []
        while revision_str:
            rev_1, remains = Dpkg.get_alphas(revision_str)
            rev_2, remains = Dpkg.get_digits(remains)
            result.extend([rev_1, rev_2])
            revision_str = remains
        return result

    # pylint: disable=invalid-name,too-many-return-statements
    @staticmethod
    def dstringcmp(a, b):
        """debian package version string section lexical sort algorithm

        "The lexical comparison is a comparison of ASCII values modified so
        that all the letters sort earlier than all the non-letters and so that
        a tilde sorts before anything, even the end of a part."
        """

        if a == b:
            return 0
        try:
            for i, char in enumerate(a):
                if char == b[i]:
                    continue
                # "a tilde sorts before anything, even the end of a part"
                # (emptyness)
                if char == '~':
                    return -1
                if b[i] == '~':
                    return 1
                # "all the letters sort earlier than all the non-letters"
                if char.isalpha() and not b[i].isalpha():
                    return -1
                if not char.isalpha() and b[i].isalpha():
                    return 1
                # otherwise lexical sort
                if ord(char) > ord(b[i]):
                    return 1
                if ord(char) < ord(b[i]):
                    return -1
        except IndexError:
            # a is longer than b but otherwise equal, hence greater
            # ...except for goddamn tildes
            if char == '~':
                return -1
            return 1
        # if we get here, a is shorter than b but otherwise equal, hence lesser
        # ...except for goddamn tildes
        if b[len(a)] == '~':
            return 1
        return -1

    @staticmethod
    def compare_revision_strings(rev1, rev2):
        """Compare two debian revision strings as described at
        https://www.debian.org/doc/debian-policy/ch-controlfields.html#s-f-Version
        """
        if rev1 == rev2:
            return 0
        # listify pads results so that we will always be comparing ints to ints
        # and strings to strings (at least until we fall off the end of a list)
        list1 = Dpkg.listify(rev1)
        list2 = Dpkg.listify(rev2)
        if list1 == list2:
            return 0
        try:
            for i, item in enumerate(list1):
                # just in case
                if not isinstance(item, list2[i].__class__):
                    raise DpkgVersionError(
                        'Cannot compare %s to %s, something has gone horribly '
                        'awry.' % (item, list2[i]))
                # if the items are equal, next
                if item == list2[i]:
                    continue
                # numeric comparison
                if isinstance(item, int):
                    if item > list2[i]:
                        return 1
                    if item < list2[i]:
                        return -1
                else:
                    # string comparison
                    return Dpkg.dstringcmp(item, list2[i])
        except IndexError:
            # rev1 is longer than rev2 but otherwise equal, hence greater
            return 1
        # rev1 is shorter than rev2 but otherwise equal, hence lesser
        return -1

    @staticmethod
    def compare_versions(ver1, ver2):
        """Function to compare two Debian package version strings,
        suitable for passing to list.sort() and friends."""
        if ver1 == ver2:
            return 0

        # note the string conversion: the debian policy here explicitly
        # specifies ASCII string comparisons, so if you are mad enough to
        # actually cram unicode characters into your package name, you are on
        # your own.
        epoch1, upstream1, debian1 = Dpkg.split_full_version(str(ver1))
        epoch2, upstream2, debian2 = Dpkg.split_full_version(str(ver2))

        # if epochs differ, immediately return the newer one
        if epoch1 < epoch2:
            return -1
        if epoch1 > epoch2:
            return 1

        # then, compare the upstream versions
        upstr_res = Dpkg.compare_revision_strings(upstream1, upstream2)
        if upstr_res != 0:
            return upstr_res

        debian_res = Dpkg.compare_revision_strings(debian1, debian2)
        if debian_res != 0:
            return debian_res

        # at this point, the versions are equal, but due to an interpolated
        # zero in either the epoch or the debian version
        return 0
