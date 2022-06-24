#!/usr/bin/env python

import os
import sys
from copy import deepcopy
from typing import Union

import fire
import git

from packaging.version import parse as parse_semver
from packaging.version import Version

import functools

sys.setrecursionlimit(10000)

TAG_PREFIX = os.getenv('RP_TAG_PREFIX', '{self.app}-').strip('"').strip("'")


def _parse_version(self, version: Union[Version, str]):
    if isinstance(version, Version):
        _version = version
    else:
        _version = parse_semver(str(version).
                                replace(self.tag_prefix, '').
                                replace('_', '+').
                                replace('bump-', '').
                                split('-')[-1])

    if not isinstance(_version, Version) and not str(version).endswith('stable'):
        raise Exception(f'Unable to parse version: {_version} to Version type')

    return _version


def parse_version(func):
    @functools.wraps(func)
    def wrapper_parse_version(self, *args, **kwargs):
        if kwargs.get('version', None):
            kwargs['version'] = _parse_version(self, version=kwargs['version'])

        return func(self, *args, **kwargs)

    return wrapper_parse_version


class SemVer:
    def __init__(self, path, app):
        self.repo = git.Repo(path, search_parent_directories=True)
        self.app = app

        self.recursion_depth = 0

        self.current_version_depth = 0

        self.tag_prefix = TAG_PREFIX.format(self=self)

        self.build = os.getenv('BUILD', 0)

        self.tags = {str(_parse_version(self, version=x.name)): {
            'tag': x,
            'version': _parse_version(self, version=x.name),
            'is_bump': x.name.startswith('bump-')}
            for x in self.repo.tags if x.name.replace('bump-', '').startswith(self.tag_prefix)}

        self.versions = sorted([x['version'] for x in self.tags.values() if isinstance(x['version'], Version) and not x['is_bump']])

        version_tags = {}
        for tag in self.tags.values():
            if str(tag['tag'].commit) not in version_tags:
                version_tags[str(tag['tag'].commit)] = []
            if isinstance(tag['version'], Version):
                version_tags[str(tag['tag'].commit)].append(tag['version'])
        self.version_tags = {commit: sorted(versions) for commit, versions in version_tags.items() if versions}

    @parse_version
    def get_versions(self,
                     bump: str = 'major',
                     version: Union[Version, str] = '0.0.0'):
        if bump == 'build':
            _versions = [x for x in self.versions if
                         x.major == version.major and x.minor == version.minor and x.micro == version.micro]
        elif bump == 'patch':
            _versions = [x for x in self.versions if
                         x.major == version.major and x.minor == version.minor]
        elif bump == 'minor':
            _versions = [x for x in self.versions if
                         x.major == version.major]
        elif bump == 'major':
            _versions = self.versions
        else:
            raise Exception(f'Invalid bump: {bump}')

        return _versions

    @parse_version
    def get_latest_version(self,
                           bump: str = 'major',
                           version: Union[Version, str] = '0.0.0'):
        if bump == 'build':
            _versions = self.get_versions(bump='build', version=version)
            if not _versions:
                _versions.append(Version(f'{version.major}.{version.minor}.{version.micro}+{self.build}'))
        elif bump == 'patch':
            _versions = self.get_versions(bump='patch', version=version)
            if not _versions:
                _versions.append(Version(f'{version.major}.{version.minor}.0+{self.build}'))
        elif bump == 'minor':
            _versions = self.get_versions(bump='minor', version=version)
            if not _versions:
                _versions.append(Version(f'{version.major}.0.0+{self.build}'))
        elif bump == 'major':
            _versions = self.get_versions(bump='major', version=version)
            if not _versions:
                _versions.append(Version(f"0.0.0+{self.build}"))
        else:
            raise Exception(f'Invalid bump: {bump}')

        return _versions[-1]

    @parse_version
    def get_next_version(self,
                         bump: str = 'patch',
                         version: Union[Version, str] = '0.0.0'):
        latest_version = self.get_latest_version(bump=bump, version=version)

        if bump == 'build':
            next_version = Version(f'{version.public}+{self.build}')
        elif bump == 'patch':
            if latest_version in self.versions:
                next_version = Version(f'{latest_version.major}.{latest_version.minor}.{latest_version.micro + 1}+{self.build}')
            else:
                next_version = Version(f'{latest_version.major}.{latest_version.minor}.{latest_version.micro}+{self.build}')
        elif bump == 'minor':
            if latest_version in self.versions:
                next_version = Version(f'{latest_version.major}.{latest_version.minor + 1}.0+{self.build}')
            else:
                next_version = Version(f'{latest_version.major}.{latest_version.minor}.0+{self.build}')
        elif bump == 'major':
            if latest_version in self.versions:
                next_version = Version(f'{latest_version.major + 1}.0.0+{self.build}')
            else:
                next_version = Version(f'{latest_version.major}.0.0+{self.build}')
        else:
            raise Exception(f'Invalid bump: {bump}')

        return next_version

    def get_current_version(self,
                            target: Version = None,
                            register=None,
                            ref='HEAD',
                            processed_refs=None,
                            depth=None,
                            current_depth=0):
        if depth is None:
            depth = 0

        if register is None:
            register = {Version('0.0.0rc0'): depth}

        if processed_refs is None:
            processed_refs = []

        try:
            _ref = self.repo.commit(ref)  # Catches situation where parent is part of a merge commit
        except ValueError:
            return False

        if _ref not in processed_refs:
            processed_refs.append(_ref)
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
                if current_depth == depth:
                    depth += 1

                for parent in _ref.parents:
                    self.get_current_version(target=target,
                                             ref=parent.hexsha,
                                             register=register,
                                             processed_refs=processed_refs,
                                             depth=depth,
                                             current_depth=deepcopy(depth))
            else:
                register[version] = depth

        current_version = sorted(register.keys())[-1]

        if ref == 'HEAD':
            self.current_version_depth = register[current_version]
        return current_version

    @parse_version
    def can_bump_to(self,
                    bump: str = 'patch',
                    version: Union[Version, str, None] = None):
        current_version = self.get_current_version()
        if version is None:
            version = self.get_next_version(bump=bump, version=current_version)

        versions = self.get_versions(bump=bump, version=self.get_next_version(bump=bump, version=version))

        if versions:
            latest_tagged_version = self.get_latest_version(bump=bump, version=versions[-1])
            ancestor_version = self.get_current_version(target=latest_tagged_version)
            if ancestor_version == Version('0.0.0rc0'):
                raise EnvironmentError(f'Unable to {bump} bump {self.app} {current_version} to {version} '
                                       f'unless {latest_tagged_version} (Latest tagged version) is an ancestor.  '
                                       f'You probably need to rebase/branch from latest tagged version.')

        if version in versions and bump != 'build':
            raise EnvironmentError(f'Unable to {bump} bump {self.app}. Version {version} has already been tagged!')

        versions.append(version)
        versions.sort()

        is_older_version = False
        if version.micro != 0:
            if bump == 'build':
                if version != versions[-1]:
                    is_older_version = True
            else:
                if version.public != versions[-1].public:
                    is_older_version = True

        if is_older_version is True:
            raise EnvironmentError(
                f'Unable to {bump} bump {self.app}. Version {version} is not newer then {versions[-1]}!')

        return versions[-1]


def dotenv(version: Version, semver):
    lines = [
        f'VERSION={version.public}',
        f'CURRENT_VERSION={semver.get_current_version()}',
        f'RELEASE_SEMVER={version}',
        f'VERSION_MAJOR={version.major}',
        f'VERSION_MINOR={version.minor}',
        f'TAG_PREFIX={semver.tag_prefix}'
    ]
    with open('semver.env', 'w') as f:
        f.writelines(line + '\n' for line in lines if line)


if __name__ == "__main__":
    semver = SemVer('.', app=os.getenv('APP'))

    FULL_VERSION = os.getenv('VERSION')

    if FULL_VERSION == "$VERSION":
        FULL_VERSION = None

    if FULL_VERSION:
        FULL_VERSION = f'{FULL_VERSION}+{semver.build}'

    __version = semver.can_bump_to(bump=os.getenv('RP_BUMP', 'patch'),
                                   version=FULL_VERSION)

    fire.Fire({
        'get': lambda: __version.public,
        'get-semver': lambda: __version,
        'get-current': lambda: semver.get_current_version(),
        'get-minor': lambda: __version.minor,
        'get-major': lambda: __version.major,
        'get-patch': lambda: __version.micro,
        'get-tag-prefix': lambda: semver.tag_prefix,
        'current-version-depth': lambda: semver.current_version_depth,
        'gen-dotenv': lambda: dotenv(__version, semver)
    })
