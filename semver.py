#!/usr/bin/env python

import os
from typing import Union

import fire
import git

from packaging.version import parse as parse_semver
from packaging.version import Version

import functools


def parse_version(func):
    @functools.wraps(func)
    def wrapper_parse_version(*args, **kwargs):
        if kwargs.get('version', None) and not isinstance(kwargs['version'], Version):
            kwargs['version'] = parse_semver(kwargs['version'])

            if not isinstance(kwargs['version'], Version):
                raise Exception(f'Unable to parse version: {kwargs["version"]} to Version type')

        return func(*args, **kwargs)

    return wrapper_parse_version


class SemVer:
    def __init__(self, path, app):
        self.repo = git.Repo(path, search_parent_directories=True)
        self.app = app

        for remote in self.repo.remotes:
            remote.fetch()

        self.tags = {x.name.split('-')[-1]: {'tag': x, 'version': parse_semver(x.name.split('-')[-1])} for x in
                     self.repo.tags if x.name.startswith(f'{self.app}-')}

        self.versions = sorted([x['version'] for x in self.tags.values() if isinstance(x['version'], Version)])

        version_tags = {}
        for tag in self.tags.values():
            if str(tag['tag'].commit) not in version_tags:
                version_tags[str(tag['tag'].commit)] = []
            if isinstance(tag['version'], Version):
                version_tags[str(tag['tag'].commit)].append(tag['version'])
        self.version_tags = {commit: sorted(versions) for commit, versions in version_tags.items()}

    @parse_version
    def get_versions(self,
                     bump: str = 'major',
                     version: Union[Version, str] = '0.0.0'):
        if bump == 'patch':
            _versions = [x for x in self.versions if
                         x.major == version.major and x.minor == version.minor]
        elif bump == 'minor':
            _versions = [x for x in self.versions if
                         x.major == version.major]
        elif bump == 'major':
            _versions = [x for x in self.versions]
        else:
            raise Exception(f'Invalid bump: {bump}')

        return _versions

    @parse_version
    def get_latest_version(self,
                           bump: str = 'major',
                           version: Union[Version, str] = '0.0.0'):
        if bump == 'patch':
            _versions = self.get_versions(bump='patch', version=version)
            if not _versions:
                _versions.append(Version(f'{version.major}.{version.minor}.0'))
        elif bump == 'minor':
            _versions = self.get_versions(bump='minor', version=version)
            if not _versions:
                _versions.append(Version(f'{version.major}.0.0'))
        elif bump == 'major':
            _versions = self.get_versions(bump='major', version=version)
            if not _versions:
                _versions.append(Version("0.0.0"))
        else:
            raise Exception(f'Invalid bump: {bump}')

        return _versions[-1]

    def get_next_version(self,
                         bump: str = 'patch',
                         version: Union[Version, str] = '0.0.0'):
        latest_version = self.get_latest_version(bump=bump, version=version)

        if bump == 'patch':
            if latest_version in self.versions:
                next_version = Version(f'{latest_version.major}.{latest_version.minor}.{latest_version.micro + 1}')
            else:
                next_version = Version(f'{latest_version.major}.{latest_version.minor}.{latest_version.micro}')
        elif bump == 'minor':
            if latest_version in self.versions:
                next_version = Version(f'{latest_version.major}.{latest_version.minor + 1}.0')
            else:
                next_version = Version(f'{latest_version.major}.{latest_version.minor}.0')
        elif bump == 'major':
            if latest_version in self.versions:
                next_version = Version(f'{latest_version.major + 1}.0.0')
            else:
                next_version = Version(f'{latest_version.major}.0.0')
        else:
            raise Exception(f'Invalid bump: {bump}')

        return next_version

    def get_current_version(self,
                            target: Version = None,
                            ref='HEAD'):
        _ref = self.repo.commit(ref)

        if _ref.hexsha in self.version_tags:
            if target:
                if target in self.version_tags[_ref.hexsha]:
                    return target
                else:
                    for parent in _ref.parents:
                        return self.get_current_version(target=target, ref=parent.hexsha)
            else:
                return self.version_tags[_ref.hexsha][-1]
        else:
            for parent in _ref.parents:
                return self.get_current_version(target=target, ref=parent.hexsha)

        return Version('0.0.0rc')

    @parse_version
    def can_bump_to(self,
                    bump: str = 'patch',
                    version: Union[Version, str, None] = None,
                    ignore_already_tagged: Union[bool, None] = None):
        if version is None:
            version = self.get_next_version(bump=bump, version=self.get_current_version())

        versions = self.get_versions(bump=bump, version=self.get_next_version(bump=bump, version=version))

        if versions:
            current_version = self.get_current_version()
            latest_tagged_version = self.get_latest_version(bump=bump, version=versions[-1])
            ancestor_version = self.get_current_version(target=latest_tagged_version)
            if ancestor_version == Version('0.0.0rc'):
                raise EnvironmentError(f'Unable to {bump} bump {self.app} {current_version.base_version} to {version} '
                                       f'unless {latest_tagged_version} (Latest tagged version) is an ancestor.  '
                                       f'You probably need to rebase/branch from latest tagged version.')

        if version in versions and ignore_already_tagged is None:
            raise EnvironmentError(f'Unable to {bump} bump {self.app}. Version {version} has already been tagged!')

        versions.append(version)
        versions.sort()

        if version != versions[-1]:
            raise EnvironmentError(f'Unable to {bump} bump {self.app}. Version {version} is not greater then {versions[-1]}!')

        return version


if __name__ == "__main__":
    semver = SemVer('.', app=os.getenv('APP'))
    _bump = os.getenv('BUMP', 'patch')
    _version = os.getenv('VERSION')

    if _version is None:
        _version = semver.can_bump_to(bump=_bump, ignore_already_tagged=os.getenv('IGNORE_ALREADY_TAGGED'))
    else:
        _version = semver.can_bump_to(bump=_bump, version=_version, ignore_already_tagged=os.getenv('IGNORE_ALREADY_TAGGED'))

    fire.Fire({
        'get': lambda: _version.base_version,
        'get-current': lambda: semver.get_current_version().base_version,
        'get-minor': lambda: _version.minor,
        'get-major': lambda: _version.major,
        'get-patch': lambda: _version.micro,
    })
