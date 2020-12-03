#!/usr/bin/env python
import os
from packaging import version as semver

import fire
import git

pre_release_placeholder = 'SNAPSHOT'
version_filepath = os.path.join('.', 'VERSION')

repo = git.Repo(os.getcwd(), search_parent_directories=True)
head = repo.commit('HEAD')
for remote in repo.remotes:
    fetch_info = remote.fetch()
    # assert fetch_info[0].commit == head, \
    #     '!!! HEAD is currently behind origin. Unable to continue.  Pull/Rebase and try again! '
tags = [x for x in repo.tags if x.name.startswith(os.environ['APP'])]
versions = [x for x in sorted([semver.parse(x.name.split('-')[-1]) for x in tags]) if isinstance(x, semver.Version)]


def get(ignore_version_match: bool = False):
    try:
        with open(version_filepath, 'r') as version_file:
            version_raw = version_file.readline()
    except FileNotFoundError:
        version_raw = f'0.0.0-{pre_release_placeholder}'

    try:
        version = semver.parse(version_raw.replace(f'-{pre_release_placeholder}', os.getenv('PRE_RELEASE', '')))
    except Exception as e:
        raise Exception(f'!!!Version "{version_raw}" is malformed', e)

    try:
        latest_patch_version = can_bump('patch', version, ignore_version_match)[-1]
    except IndexError:
        latest_patch_version = version

    try:
        patch_tag = [x for x in tags if x.name.endswith(str(latest_patch_version))][0]
        patch = repo.commit(patch_tag.name)

        assert len(repo.merge_base(patch, head)) > 0, \
            f"No common ancestor between latest tagged/released patch version " \
            f"{latest_patch_version} with ref '{patch}' and HEAD ref '{head}'"
    except IndexError:
        pass

    return version


def write_version_file(version: semver.Version):
    version = f'{version.major}.{version.minor}.{version.micro}-{pre_release_placeholder}'
    with open(version_filepath, 'w') as version_file:
        version_file.write(version)


def get_minor():
    version = get()

    return f"{version.major}.{version.minor}"


def get_major():
    version = get()

    return f"{version.major}"


def can_bump(bump, version, ignore_version_match: bool = False):
    if not ignore_version_match:
        assert version not in versions, f'!!! Version "{version}" has already been tagged/released!'

    if bump == 'patch':
        _versions = sorted(list(set([f'{x.major}.{x.minor}.{x.micro}' for x in versions if
                                    x.major == version.major and x.minor == version.minor and x.micro > version.micro])))

        assert len(_versions) == 0, f'!!! Would not be able to bump patch version ' \
                                    f'{version.major}.{version.minor}.{int(version.micro) + 1}. ' \
                                    f'Version(s) {", ".join(_versions)} already been tagged/released!'

        return _versions

    if bump == 'minor':
        _versions = sorted(list(set([f'{x.major}.{x.minor}' for x in versions if
                                    x.major == version.major and x.minor > version.minor])))

        assert len(_versions) == 0, f'!!! Would not be able to bump minor version ' \
                                    f'{version.major}.{int(version.minor) + 1}. ' \
                                    f'Version(s) {", ".join(_versions)} already been tagged/released!'

        can_bump('patch', version)

        return _versions

    if bump == 'major':
        _versions = sorted(list(set([f'{x.major}' for x in versions if
                                    x.major > version.major])))

        assert len(_versions) == 0, f'!!! Would not be able to bump major version ' \
                                    f'{version.major + 1}. ' \
                                    f'Version(s) {", ".join(_versions)} already been tagged/released!'

        can_bump('minor', version)

        return _versions

    raise Exception(f'Can bump got invalid bump value {bump}. Must be patch, minor, major.')


def inc_patch(dry_run: bool = False):
    version = get(ignore_version_match=True)

    can_bump('patch', version, ignore_version_match=True)

    next_version = semver.Version(f'{version.major}.{version.minor}.{int(version.micro) + 1}')

    if not dry_run:
        write_version_file(next_version)

    return str(next_version)


def inc_minor(dry_run: bool = False):
    version = get(ignore_version_match=True)

    can_bump('minor', version, ignore_version_match=True)

    next_version = semver.Version(f'{version.major}.{int(version.minor) + 1}.0')

    if not dry_run:
        write_version_file(next_version)

    return str(next_version)


def inc_major(dry_run: bool = False):
    version = get(ignore_version_match=True)

    can_bump('major', version, ignore_version_match=True)

    next_version = semver.Version(f'{int(version.major) + 1}.0.0')

    if not dry_run:
        write_version_file(next_version)

    return str(next_version)


if __name__ == "__main__":
    fire.Fire({
        'get': get,
        'get-ignore-version-match': lambda: get(ignore_version_match=True),
        'get-base-version': lambda: get().base_version,
        'get-minor': get_minor,
        'get-major': get_major,

        'can-patch': lambda: can_bump('patch', get().base_version),
        'inc-patch': inc_patch,

        'can-minor': lambda: can_bump('minor', get().base_version),
        'inc-minor': inc_minor,

        'can-major': lambda: can_bump('major', get().base_version),
        'inc-major': inc_major,
    })
