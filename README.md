# python-dpkg

This library can be used to:

1. read and extract control data from Debian-format package files, even
   on platforms that generally lack a native implementation of dpkg

2. compare dpkg version strings, using a pure Python implementation of
   the algorithm described in section 5.6.12 of the debian-policy manual:
   https://www.debian.org/doc/debian-policy/ch-controlfields.html#version

3. Parse debian source description (dsc) files, inspect their contents
   and verify that their source files are present and checksums are
   correct.

This is primarily intended for use on platforms that do not normally
ship [python-apt](http://apt.alioth.debian.org/python-apt-doc/) due to
licensing restrictions or the lack of a native libapt.so (e.g. macOS)

Currently only tested on CPython 3.x, but at least in theory should run
on any python distribution that can install the [arpy](https://pypi.python.org/pypi/arpy/)
library.

Note: python 2.7 compatibility was removed in version 1.4.0 and the v1.3
branch is no longer being maintained. This means that among other issues,
support for zstandard-compressed deb packages will not be available on
py27 -- consider this impetus to upgrade if you have not already.

## Installing

Install the 'pydpkg' package from [PyPi](https://pypi.python.org) using
the [pip](https://packaging.python.org/installing/) tool:

    $ pip install pydpkg
    Collecting pydpkg
      Downloading pydpkg-1.1-py2-none-any.whl
      Installing collected packages: pydpkg
      Successfully installed pydpkg-1.1

## Developing

python-dpkg uses [Poetry](https://python-poetry.org/) to manage its dependencies.

The [Makefile](Makefile) will attempt to set up a reasonable build/test
environment on both macOS/Darwin and more traditional unixes (linux, freebsd,
etc), but relies on the existence of [pyenv](https://github.com/pyenv/pyenv),
[pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv) everywhere and
[Homebrew](https://brew.sh) on macOS.  You don't _need_ to use the workflow
that the makefile enforces (modern versions of [pip](https://pypi.org/project/pip/)
will happily digest `pyproject.toml` files and you can run the test commands
manually) but please ensure all tests pass before submitting PRs.

## Usage

### Binary Packages

#### Read and extract headers

    >>> from pydpkg import Dpkg
    >>> dp = Dpkg('/tmp/testdeb_1:0.0.0-test_all.deb')

    >>> dp.headers
    {'maintainer': u'Climate Corp Engineering <no-reply@climate.com>', 'description': u'testdeb\n a bogus debian package for testing dpkg builds', 'package': u'testdeb', 'section': u'base', 'priority': u'extra', 'installed-size': u'0', 'version': u'1:0.0.0-test', 'architecture': u'all'}

    >>> print(dp)
    Package: testdeb
    Version: 1:0.0.0-test
    Section: base
    Priority: extra
    Architecture: all
    Installed-Size: 0
    Maintainer: Climate Corp Engineering <no-reply@climate.com>
    Description: testdeb
     a bogus debian package for testing dpkg builds

#### Interact directly with the package control message

    >>> dp.message
    <email.message.Message instance at 0x10895c6c8>
    >>> dp.message.get_content_type()
    'text/plain'

#### Get package file fingerprints

    >>> dp.fileinfo
    {'sha256': '547500652257bac6f6bc83f0667d0d66c8abd1382c776c4de84b89d0f550ab7f', 'sha1': 'a5d28ae2f23e726a797349d7dd5f21baf8aa02b4', 'filesize': 910, 'md5': '149e61536a9fe36374732ec95cf7945d'}
    >>> dp.md5
    '149e61536a9fe36374732ec95cf7945d'
    >>> dp.sha1
    'a5d28ae2f23e726a797349d7dd5f21baf8aa02b4'
    >>> dp.sha256
    '547500652257bac6f6bc83f0667d0d66c8abd1382c776c4de84b89d0f550ab7f'
    >>> dp.filesize
    910

#### Get the components of the package version

    >>> d.epoch
    1
    >>> d.upstream_version
    u'0.0.0'
    >>> d.debian_revision
    u'test'

#### Get an arbitrary control header, case-independent

    >>> d.version
    u'1:0.0.0-test'
    
    >>> d.VERSION
    u'1:0.0.0-test'
    
    >>> d.description
    u'testdeb\n a bogus debian package for testing dpkg builds'
    
    >>> d.get('nosuchheader', 'default')
    'default'

#### Compare current version to a candidate version

    >>> dp.compare_version_with('1.0')
    1

    >>> dp.compare_version_with('1:1.0')
    -1

#### Compare two arbitrary version strings

    >>> from pydpkg import Dpkg
    >>> ver_1 = '0:1.0-test1'
    >>> ver_2 = '0:1.0-test2'
    >>> Dpkg.compare_versions(ver_1, ver_2)
    -1

#### Use as a key function to sort a list of version strings

    >>> from pydpkg import Dpkg
    >>> sorted(['0:1.0-test1', '1:0.0-test0', '0:1.0-test2'] , key=Dpkg.compare_versions_key)
    ['0:1.0-test1', '0:1.0-test2', '1:0.0-test0']

#### Use the `dpkg-inspect` script to inspect packages

    $ dpkg-inspect ~/testdeb*deb
    Filename: /Home/n/testdeb_1:0.0.0-test_all.deb
    Size:     910
    MD5:      149e61536a9fe36374732ec95cf7945d
    SHA1:     a5d28ae2f23e726a797349d7dd5f21baf8aa02b4
    SHA256:   547500652257bac6f6bc83f0667d0d66c8abd1382c776c4de84b89d0f550ab7f
    Headers:
      Package: testdeb
      Version: 1:0.0.0-test
      Section: base
      Priority: extra
      Architecture: all
      Installed-Size: 0
      Maintainer: Nathan Mehl <n@climate.com>
      Description: testdeb
       a bogus debian package for testing dpkg builds

### Source Packages

#### Read and extract headers

    >>> from pydpkg import Dsc
    >>> dsc = Dsc('testdeb_0.0.0.dsc')
    >>> dsc.standards_version
    '3.9.6'
    >>> dsc.format
    '3.0 (quilt)'
    >>> x.build_depends
    'python (>= 2.6.6-3), debhelper (>= 9)'

#### Get the full set of dsc headers as a dictionary

    >>> dsc.headers
    {'Architecture': 'all',
     'Binary': 'testdeb',
     'Build-Depends': 'python (>= 2.6.6-3), debhelper (>= 9)',
     'Checksums-Sha1': ' f250ac0a426b31df24fc2c98050f4fab90e456cd 280 testdeb_0.0.0.orig.tar.gz\n cb3474ff94053018957ebcf1d8a2b45f75dda449 232 testdeb_0.0.0-1.debian.tar.xz\n 80cd7b01014a269d445c63b037b885d6002cf533 841 testdeb_0.0.0.dsc',
     'Checksums-Sha256': ' aa57ba8f29840383f5a96c5c8f166a9e6da7a484151938643ce2618e82bfeea7 280 testdeb_0.0.0.orig.tar.gz\n 1ddb2a7336a99bc1d203f3ddb59f6fa2d298e90cb3e59cccbe0c84e359979858 232 testdeb_0.0.0-1.debian.tar.xz\n b5ad1591349eb48db65e6865be506ad7dbd21931902a71addee5b1db9ae1ac2a 841 testdeb_0.0.0.dsc',
     'Files': ' 142ca7334ed1f70302b4504566e0c233 280 testdeb_0.0.0.orig.tar.gz\n fc80e6e7f1c1a08b78a674aaee6c1548 232 testdeb_0.0.0-1.debian.tar.xz\n 893d13a2ef13f7409c9521e8ab1dbccb 841 testdeb_0.0.0.dsc',
     'Format': '3.0 (quilt)',
     'Homepage': 'https://github.com/TheClimateCorporation',
     'Maintainer': 'Nathan J. Mehl <n@climate.com>',
     'Package-List': 'testdeb',
     'Source': 'testdeb',
     'Standards-Version': '3.9.6',
     'Uploaders': 'Nathan J. Mehl <n@climate.com>',
     'Version': '0.0.0-1'}

#### Interact directly with the dsc message

    >>> dsc.message
    <email.message.Message instance at 0x106fedea8>
    >>> dsc.message.get_content_type()
    'text/plain'
    >>> dsc.message.get('uploaders')
    'Nathan J. Mehl <n@climate.com>'

#### Render the dsc message as a string

    >>> print(dsc)
    Format: 3.0 (quilt)
    Source: testdeb
    Binary: testdeb
    Architecture: all
    Version: 0.0.0-1
    Maintainer: Nathan J. Mehl <n@climate.com>
    Uploaders: Nathan J. Mehl <n@climate.com>
    Homepage: https://github.com/TheClimateCorporation
    Standards-Version: 3.9.6
    Build-Depends: python (>= 2.6.6-3), debhelper (>= 9)
    Package-List: testdeb
    Checksums-Sha1:
     f250ac0a426b31df24fc2c98050f4fab90e456cd 280 testdeb_0.0.0.orig.tar.gz
     cb3474ff94053018957ebcf1d8a2b45f75dda449 232 testdeb_0.0.0-1.debian.tar.xz
     80cd7b01014a269d445c63b037b885d6002cf533 841 testdeb_0.0.0.dsc
    Checksums-Sha256:
     aa57ba8f29840383f5a96c5c8f166a9e6da7a484151938643ce2618e82bfeea7 280 testdeb_0.0.0.orig.tar.gz
     1ddb2a7336a99bc1d203f3ddb59f6fa2d298e90cb3e59cccbe0c84e359979858 232 testdeb_0.0.0-1.debian.tar.xz
     b5ad1591349eb48db65e6865be506ad7dbd21931902a71addee5b1db9ae1ac2a 841 testdeb_0.0.0.dsc
    Files:
     142ca7334ed1f70302b4504566e0c233 280 testdeb_0.0.0.orig.tar.gz
     fc80e6e7f1c1a08b78a674aaee6c1548 232 testdeb_0.0.0-1.debian.tar.xz
     893d13a2ef13f7409c9521e8ab1dbccb 841 testdeb_0.0.0.dsc

#### List the package source files from the dsc

    >>> dsc.source_files
    ['/tmp/testdeb_0.0.0.orig.tar.gz',
     '/tmp/testdeb_0.0.0-1.debian.tar.xz',
     '/tmp/testdeb_0.0.0.dsc' ]

#### Validate that the package source files are present

    >>> dsc.missing_files
    []
    >>> dsc.all_files_present
    True
    >>> dsc.validate()
    >>>

    >>> bad = Dsc('testdeb_1.1.1-bad.dsc')
    >>> bad.missing_files
    ['/tmp/testdeb_1.1.1.orig.tar.gz', '/tmp/testdeb_1.1.1-1.debian.tar.xz']
    >>> bad.all_files_present
    False
    >>> bad.validate()
    pydpkg.DscMissingFileError: ['/tmp/testdeb_1.1.1.orig.tar.gz', '/tmp/testdeb_1.1.1-1.debian.tar.xz']

#### Inspect the source file checksums from the dsc

    >>> pp(dsc.checksums)
    {'md5': {'/tmp/testdeb_0.0.0-1.debian.tar.xz': 'fc80e6e7f1c1a08b78a674aaee6c1548',
             '/tmp/testdeb_0.0.0.dsc': '893d13a2ef13f7409c9521e8ab1dbccb',
             '/tmp/testdeb_0.0.0.orig.tar.gz': '142ca7334ed1f70302b4504566e0c233'},
     'sha1': {'/tmp/testdeb_0.0.0-1.debian.tar.xz': 'cb3474ff94053018957ebcf1d8a2b45f75dda449',
              '/tmp/testdeb_0.0.0.dsc': '80cd7b01014a269d445c63b037b885d6002cf533',
              '/tmp/testdeb_0.0.0.orig.tar.gz': 'f250ac0a426b31df24fc2c98050f4fab90e456cd'},
     'sha256': {'/tmp/testdeb_0.0.0-1.debian.tar.xz': '1ddb2a7336a99bc1d203f3ddb59f6fa2d298e90cb3e59cccbe0c84e359979858',
                '/tmp/testdeb_0.0.0.dsc': 'b5ad1591349eb48db65e6865be506ad7dbd21931902a71addee5b1db9ae1ac2a',
                '/tmp/testdeb_0.0.0.orig.tar.gz': 'aa57ba8f29840383f5a96c5c8f166a9e6da7a484151938643ce2618e82bfeea7'}}

#### Validate that all source file checksums are correct

    >>> dsc.corrected_checksums
    {}
    >>> dsc.all_checksums_correct
    True
    >>> dsc.validate()
    >>>

    >>> bad = Dsc('testdeb_0.0.0-badchecksums.dsc')
    >>> bad.corrected_checksums
    {'sha256': defaultdict(None, {'/tmp/testdeb_0.0.0-1.debian.tar.xz': '1ddb2a7336a99bc1d203f3ddb59f6fa2d298e90cb3e59cccbe0c84e359979858', '/tmp/testdeb_0.0.0.orig.tar.gz': 'aa57ba8f29840383f5a96c5c8f166a9e6da7a484151938643ce2618e82bfeea7'}), 'sha1': defaultdict(None, {'/tmp/testdeb_0.0.0-1.debian.tar.xz': 'cb3474ff94053018957ebcf1d8a2b45f75dda449', '/tmp/testdeb_0.0.0.orig.tar.gz': 'f250ac0a426b31df24fc2c98050f4fab90e456cd'})}
    >>> bad.all_checksums_correct
    False
    >>> bad.validate()
    pydpkg.DscBadChecksumsError: {'sha256': defaultdict(None, {'/tmp/testdeb_0.0.0-1.debian.tar.xz': '1ddb2a7336a99bc1d203f3ddb59f6fa2d298e90cb3e59cccbe0c84e359979858', '/tmp/testdeb_0.0.0.orig.tar.gz': 'aa57ba8f29840383f5a96c5c8f166a9e6da7a484151938643ce2618e82bfeea7'}), 'sha1': defaultdict(None, {'/tmp/testdeb_0.0.0-1.debian.tar.xz': 'cb3474ff94053018957ebcf1d8a2b45f75dda449', '/tmp/testdeb_0.0.0.orig.tar.gz': 'f250ac0a426b31df24fc2c98050f4fab90e456cd'})}
