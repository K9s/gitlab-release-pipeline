import os
import shutil

import pytest
from packaging.version import Version

from semver import SemVer

from git import Repo

expected_versions = {
    '0.0.1': None,
    '0.0.2': None,
    '0.0.3': None,
    '0.1.0': None,
    '0.1.1': None,
    '0.1.2': None,
    '0.1.15': None,
    '0.2.0': None,
    '0.2.1': None,
    '1.0.0': None,
    '4.0.0': None
}
head = None


def get_expected_version(version: str):
    build_num = expected_versions[version]
    return Version(f'{version}+{build_num}')


def create_test_repo(path):
    global head
    try:
        shutil.rmtree(path)
    except FileNotFoundError:
        pass

    assert os.path.isdir(path) is False

    repo = Repo.init(os.path.join('.', path))

    index = repo.index

    buildnum = 0
    for version in expected_versions.keys():
        buildnum += 1
        expected_versions[version] = buildnum
        open(f'{path}/{version}', 'w').write('Initial Commit\n')
        index.add(version)
        version_commit = index.commit(f'Commit {version}')
        repo.create_tag(f'test-{version}+{buildnum}', ref=version_commit)
        open(f'{path}/{version}', 'a').write('commit 1\n')
        index.add(version)
        index.commit(f'{version} commit 1')
        open(f'{path}/{version}', 'a').write('commit 2\n')
        index.add(version)
        head = index.commit(f'{version} commit 2')

    return repo.working_dir


working_dir = create_test_repo(path='test-repo')
semver = SemVer(working_dir, 'test')


def test_can_get_repo():
    repo = semver.repo
    assert isinstance(repo, Repo)


def test_get_version_multi_digit_not_lexicographic():
    assert semver.get_latest_version(bump='patch', version='0.1.1') != Version('0.1.2')


def test_get_version_patch_bump():
    assert semver.get_latest_version(bump='patch', version='0.0.0') == get_expected_version('0.0.3')
    assert semver.get_latest_version(bump='patch', version='0.0.2') == get_expected_version('0.0.3')
    assert semver.get_latest_version(bump='patch', version='0.2.0') == get_expected_version('0.2.1')
    assert semver.get_latest_version(bump='patch', version='0.2.100') == get_expected_version('0.2.1')
    assert semver.get_latest_version(bump='patch', version='0.2.1') == get_expected_version('0.2.1')
    assert semver.get_latest_version(bump='patch', version='9.8.7') == Version('9.8.0+0')


def test_get_version_minor_bump():
    assert semver.get_latest_version(bump='minor', version='0.0.0') == get_expected_version('0.2.1')
    assert semver.get_latest_version(bump='minor', version='0.1.0') == get_expected_version('0.2.1')
    assert semver.get_latest_version(bump='minor', version='0.1.100') == get_expected_version('0.2.1')
    assert semver.get_latest_version(bump='minor', version='1.0.0') == get_expected_version('1.0.0')
    assert semver.get_latest_version(bump='minor', version='2.0.0') == Version('2.0.0+0')
    assert semver.get_latest_version(bump='minor', version='9.8.7') == Version('9.0.0+0')


def test_get_version_major_bump():
    assert semver.get_latest_version(bump='major', version='0.0.0') == get_expected_version('4.0.0')
    assert semver.get_latest_version(bump='major', version='0.1.0') == get_expected_version('4.0.0')
    assert semver.get_latest_version(bump='major', version='0.1.100') == get_expected_version('4.0.0')
    assert semver.get_latest_version(bump='major', version='2.0.0') == get_expected_version('4.0.0')
    assert semver.get_latest_version(bump='major', version='9.8.7') == get_expected_version('4.0.0')


def test_get_version_same_as_latest():
    assert semver.get_latest_version(bump='patch', version='0.1.15') == get_expected_version('0.1.15')
    assert semver.get_latest_version(bump='minor', version='1.0.0') == get_expected_version('1.0.0')
    assert semver.get_latest_version(bump='major', version='4.0.0') == get_expected_version('4.0.0')


def test_can_get_next_version_patch():
    assert semver.get_next_version(bump='patch', version=Version('0.0.0')) == Version('0.0.4+0')
    assert semver.get_next_version(bump='patch', version=Version('0.1.2')) == Version('0.1.16+0')
    assert semver.get_next_version(bump='patch', version=Version('0.1.15')) == Version('0.1.16+0')


def test_can_get_next_version_minor():
    assert semver.get_next_version(bump='minor', version=Version('0.0.0')) == Version('0.3.0+0')


def test_can_get_next_version_major():
    assert semver.get_next_version(bump='major', version=Version('0.0.0')) == Version('5.0.0+0')


def test_can_bump():
    # These versions already have tagged versions that would fail but don't because we're allowing the tag to exist
    assert semver.can_bump_to(bump='build', version=Version('0.0.3+20')) == Version('0.0.3+20')
    assert semver.can_bump_to(bump='build', version=Version('0.2.1+20')) == Version('0.2.1+20')
    assert semver.can_bump_to(bump='build', version=Version('4.0.0+20')) == Version('4.0.0+20')

    with pytest.raises(EnvironmentError):
        semver.can_bump_to(bump='patch', version=Version('0.0.2'))  # Older then latest
        semver.can_bump_to(bump='minor', version=Version('0.0.4'))
        semver.can_bump_to(bump='major', version=Version('0.1.2'))

        semver.can_bump_to(bump='patch', version=Version('0.0.3'))
        semver.can_bump_to(bump='minor', version=Version('0.2.1'))
        semver.can_bump_to(bump='major', version=Version('4.0.0'))

    assert semver.can_bump_to(bump='patch', version=Version('0.0.4')) == Version('0.0.4')  # Next patch version
    assert semver.can_bump_to(bump='patch', version=Version('0.0.5')) == Version('0.0.5')  # Newer then next patch version
    assert semver.can_bump_to(bump='patch', version=Version('0.1.20')) == Version('0.1.20')
    assert semver.can_bump_to(bump='minor', version=Version('0.2.4')) == Version('0.2.4')
    assert semver.can_bump_to(bump='major', version=Version('4.1.2')) == Version('4.1.2')
    assert semver.can_bump_to(bump='patch', version=Version('8.1.2')) == Version('8.1.2')
    assert semver.can_bump_to(bump='minor', version=Version('8.1.2')) == Version('8.1.2')
    assert semver.can_bump_to(bump='major', version=Version('8.1.2')) == Version('8.1.2')

    assert semver.can_bump_to(bump='minor')


def test_can_get_current_version():
    # Check to see that the last commit and repo HEAD are the same (sanity check)
    assert semver.repo.commit('HEAD') == head

    assert semver.get_current_version() == get_expected_version('4.0.0')

    assert semver.get_current_version(Version('0.1.15')) == get_expected_version('0.1.15')
    assert semver.get_current_version(Version('0.1.2')) == get_expected_version('0.1.2')

    assert semver.get_current_version(Version('0.0.0')) == Version('0.0.0rc')


def test_cannot_bump_out_of_order():
    # Create branch from tagged version
    semver.repo.head.reference = semver.repo.create_head('test-feature', commit=f'test-{get_expected_version("0.1.2")}')
    semver.repo.head.reset(index=True, working_tree=True)

    # Add a commit
    open('test-repo/0.1.2', 'a').write('out-of-order commit\n')
    semver.repo.index.add('0.1.2')
    semver.repo.index.commit('out-of-order commit')

    # Check that current version is as expected
    assert semver.get_current_version() == get_expected_version('0.1.2')

    # Should not be able to bump due to 0.1.15 being a more recent version
    with pytest.raises(EnvironmentError, match=r'.*Unable to.*bump.*unless (0\.1\.15)'):
        semver.can_bump_to(bump='patch', version='0.1.20')

    # Reset HEAD to main ref
    semver.repo.head.reference = semver.repo.commit('main')
    semver.repo.head.reset(index=True, working_tree=True)
