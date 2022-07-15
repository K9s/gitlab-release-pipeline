#!/usr/bin/env python

import os
import sys
from copy import deepcopy
from typing import Union, List
import functools

import fire
import git

from packaging.version import parse as parse_semver
from packaging.version import Version

sys.setrecursionlimit(10000)


def version(func):
    @functools.wraps(func)
    def wrapper_version(self, *args, **kwargs):
        if kwargs.get('version', None):
            kwargs['version'] = self.parse_version(version=kwargs['version'])

        return func(self, *args, **kwargs)

    return wrapper_version


class Release:
    def __init__(self, path, app):
        self.repo = git.Repo(path, search_parent_directories=True)
        self.app = app

        self.recursion_depth = 0

        self.current_version_depth = 0

        self.tag_prefix = os.getenv('RP_TAG_PREFIX', '{self.app}-').strip('"').strip("'").format(self=self)

        self.build = 1

        self.tags = {str(self.parse_version(version=x.name)): {
            'tag': x,
            'version': self.parse_version(version=x.name),
            'is_bump': x.name.startswith('bump-')}
            for x in self.repo.tags if x.name.replace('bump-', '').startswith(self.tag_prefix)}

        self.tags = {key: value for (key, value) in self.tags.items() if not value['version'].is_prerelease}

        self.versions = sorted([x['version'] for x in self.tags.values() if
                                isinstance(x['version'], Version) and not x['is_bump']])

        version_tags = {}
        for tag in self.tags.values():
            if str(tag['tag'].commit) not in version_tags:
                version_tags[str(tag['tag'].commit)] = []
            if isinstance(tag['version'], Version):
                version_tags[str(tag['tag'].commit)].append(tag['version'])
        self.version_tags = {commit: sorted(versions) for commit, versions in version_tags.items() if versions}

        self.current_version = self.get_version()

    def parse_version(self, version: Union[Version, str]) -> Version:
        if isinstance(version, Version):
            _version = version
        else:
            version_str = str(str(version).
                              replace(self.tag_prefix, '').
                              replace('_', '+').
                              replace('bump-', ''))

            for tag_cleanup in [x for x in os.getenv('RP_RC_TAG_FIXUP_SUFFIXES', '').split(',') if x]:
                version_str = version_str.replace(tag_cleanup, 'rc')

            version_str = version_str.strip('.').strip('-')

            _version = parse_semver(version_str)

        if not isinstance(_version, Version) and not str(version).endswith('stable'):
            raise Exception(f'Unable to parse version: {_version} as Version')

        return _version

    @version
    def get_versions(self,
                     bump: str = 'major',
                     version: Union[Version, str] = '0.0.0') -> List[Version]:
        if bump == 'build':
            versions = [x for x in self.versions if
                        x.major == version.major and x.minor == version.minor and x.micro == version.micro]
        elif bump == 'patch':
            versions = [x for x in self.versions if
                        x.major == version.major and x.minor == version.minor]
        elif bump == 'minor':
            versions = [x for x in self.versions if
                        x.major == version.major]
        elif bump == 'major':
            versions = self.versions
        else:
            raise Exception(f'Invalid bump: {bump}')

        return deepcopy(versions)

    @version
    def get_latest_version(self,
                           bump: str = 'major',
                           version: Union[Version, str] = '0.0.0') -> Version:
        _versions = self.get_versions(bump=bump, version=version)

        if not _versions:
            if bump == 'build':
                _versions.append(Version(f'{version.major}.{version.minor}.{version.micro}+{self.build}'))
            elif bump == 'patch':
                _versions.append(Version(f'{version.major}.{version.minor}.0+{self.build}'))
            elif bump == 'minor':
                _versions.append(Version(f'{version.major}.0.0+{self.build}'))
            elif bump == 'major':
                _versions.append(Version(f"0.0.0+{self.build}"))

        return sorted(_versions)[-1]

    def get_version(self,
                    target: Version = None,
                    ref='HEAD',
                    _register=None,
                    _processed_refs=None,
                    _depth=None,
                    _current_depth=0) -> Union[Version, None]:
        if _depth is None:
            _depth = 0

        if _register is None:
            _register = {Version('0.0.0rc0'): _depth}

        if _processed_refs is None:
            _processed_refs = []

        try:
            _ref = self.repo.commit(ref)  # Catches situation where parent is part of a merge commit
        except ValueError:
            return None

        if _ref not in _processed_refs:
            _processed_refs.append(_ref)
            version = None
            if _ref.hexsha in self.version_tags:
                versions = self.version_tags[_ref.hexsha]
                if target:
                    versions = [x for x in versions if x.public == target.public]
                    if versions:
                        version = versions[-1]
                else:
                    version = versions[-1]

            if version is None:
                if _current_depth == _depth:
                    _depth += 1

                for parent in _ref.parents:
                    self.get_version(target=target,
                                     ref=parent.hexsha,
                                     _register=_register,
                                     _processed_refs=_processed_refs,
                                     _depth=_depth,
                                     _current_depth=deepcopy(_depth))
            else:
                _register[version] = _depth

        if ref == 'HEAD':
            version = sorted(_register.keys())[-1]
            self.current_version_depth = _register[version]
            return version
        return None

    @version
    def get_next_version(self,
                         bump: str = 'patch',
                         version: Union[Version, str] = '0.0.0') -> Version:
        latest = self.get_latest_version(bump=bump, version=version)

        if bump == 'build':
            next_version = Version(f'{latest.public}+{self.build}')
        elif bump == 'patch':
            if latest in self.versions:
                next_version = Version(f'{latest.major}.{latest.minor}.{latest.micro + 1}+{self.build}')
            else:
                next_version = Version(f'{latest.major}.{latest.minor}.{latest.micro}+{self.build}')
        elif bump == 'minor':
            if latest in self.versions:
                next_version = Version(f'{latest.major}.{latest.minor + 1}.0+{self.build}')
            else:
                next_version = Version(f'{latest.major}.{latest.minor}.0+{self.build}')
        elif bump == 'major':
            if latest in self.versions:
                next_version = Version(f'{latest.major + 1}.0.0+{self.build}')
            else:
                next_version = Version(f'{latest.major}.0.0+{self.build}')
        else:
            raise Exception(f'Invalid bump: {bump}')

        return next_version

    @version
    def get_bump_version(self,
                         bump: str = 'patch',
                         version: Union[Version, str, None] = None) -> Version:
        if version is None:
            version = self.get_next_version(bump=bump, version=self.current_version)

        versions = self.get_versions(bump=bump, version=self.get_next_version(bump=bump, version=version))

        if versions and not os.getenv('RP_LATEST_TAGGED_ANCESTOR_IGNORED'):
            latest_tagged_version = self.get_latest_version(bump=bump, version=versions[-1])
            ancestor_version = self.get_version(target=latest_tagged_version)
            if ancestor_version == Version('0.0.0rc0'):
                raise EnvironmentError(f'Unable to {bump} bump {self.app} {self.current_version} to {version} '
                                       f'unless {latest_tagged_version} (Latest tagged version) is an ancestor.  '
                                       f'You probably need to rebase/branch from latest tagged version.')

        if version in versions and not os.getenv('RP_IGNORE_ALREADY_TAGGED'):
            raise EnvironmentError(f'Unable to {bump} bump {self.app}. Version {version} has already been tagged!')

        versions.append(version)
        versions.sort()

        is_older_version = False
        if bump == 'build':
            if version != versions[-1]:
                is_older_version = True
        else:
            if version.public != versions[-1].public:
                is_older_version = True

        if is_older_version is True and int(self.build) > 0:
            raise EnvironmentError(
                f'Unable to {bump} bump {self.app}. Version {version} is not newer then {versions[-1]}!')

        return versions[-1]


if __name__ == "__main__":
    release = Release('.', app=os.getenv('APP'))

    SEMVER = os.getenv('SEMVER')

    BUILD = "1" if os.getenv("BUILD") == '' else os.getenv("BUILD", "1")

    if SEMVER:
        __version = release.parse_version(version=SEMVER)
        release.build = __version.local if __version.local else BUILD
    else:
        VERSION = os.getenv('VERSION')
        if VERSION == "$VERSION":
            VERSION = None

        if VERSION:
            VERSION = release.parse_version(version=VERSION)
            if not VERSION.local:
                VERSION = release.parse_version(version=f'{VERSION.public}+{BUILD}')

            if os.getenv("BUILD") and os.getenv("BUILD") != VERSION.local:
                raise EnvironmentError(
                    f'BUILD envar ({os.getenv("BUILD")}) conflicts with build from VERSION ({VERSION.local})'
                )

            release.build = VERSION.local
        else:
            release.build = BUILD

        RP_BUMP = os.getenv('RP_BUMP', 'patch')
        if RP_BUMP == "$RP_BUMP":
            RP_BUMP = 'patch'

        __version = release.get_bump_version(bump=RP_BUMP, version=VERSION)

    fire.Fire({
        'get': lambda: __version.public,
        'get-build': lambda: release.build,
        'get-current': lambda: release.current_version,
        'get-minor': lambda: __version.minor,
        'get-major': lambda: __version.major,
        'get-patch': lambda: __version.micro,
        'get-tag-prefix': lambda: release.tag_prefix,
        'current-version-depth': lambda: release.current_version_depth
    })
