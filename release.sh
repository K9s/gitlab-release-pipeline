#!/usr/bin/env bash
set -e

release_type=${1}

if [[ -z "${APP}" ]]; then
  # shellcheck disable=SC2016
  echo '$APP is unset deriving from folder name'
  app=$(basename $(realpath .))
  if [[ $app == 'src' ]]; then
    app=$(basename $(realpath ../))
  fi
  export APP=$app
fi

if [[ -n "${SEMVER}" ]]; then
    echo "⚠️ SEMVER set !!! This will result in SemVer checks being skipped! ⚠️ "
fi

if [[ -n "${RP_RELEASE_BRANCH}" ]]; then
    echo "⚠️ RP_RELEASE_BRANCH set to ${RP_RELEASE_BRANCH} !!! This overrides default assumptions around what which branch(s) can result in a release ⚠️ "
fi

# Work around the limitation where gitlab runners can't push to repos.
if [[ -z "${RELEASE_USER}" ]]; then
  echo "Using default checkout credentials"
  echo "  if push fails create an access token with repository write"
  echo "  and set RELEASE_USER and RELEASE_PASS variables"
else
  echo "Using credentials from RELEASE_USER: ${RELEASE_USER}"
  GIT_URL=$(git remote get-url origin)
  GIT_URL=$(echo ${GIT_URL} | sed -r "s/^(.+?\/\/)(.+?):(.+?)@(.+)$/\1${RELEASE_USER}:${RELEASE_PASS}@\4/")
  git remote set-url origin ${GIT_URL}
fi

project_dir=$(dirname "$0")

echo "Determining version using RP_TAG_PREFIX: ${RP_TAG_PREFIX:-'default'}"
export __APP=`echo ${APP} | tr '-' '_'`
_APP=$(python -c "import os;print(os.environ.get('__APP').upper())")
VERSION_CODE=$((${_APP}_VERSION_CODE+1))
BUILD_NUMBER="${BUILD_NUMBER:-$CI_PIPELINE_IID}"
RP_SEMVER_BUILD_REF=${RP_SEMVER_BUILD_REF:-BUILD_NUMBER}
export BUILD=$(eval echo \${"$RP_SEMVER_BUILD_REF"})
export BUILD=$("$project_dir"/semver.py get-build)

if [[ $("$project_dir"/semver.py get) == '0.0.0' ]]; then
  echo "Unable to determine version, fetching full history and trying again."
  git fetch --unshallow --quiet || true
fi
VERSION=$("$project_dir"/semver.py get)

TAG_PREFIX=$("$project_dir"/semver.py get-tag-prefix)
RELEASE_SEMVER=$("$project_dir"/semver.py get-semver)
CURRENT_VERSION=$("$project_dir"/semver.py get-current)
echo "... Current version: ${CURRENT_VERSION}, Release SemVer: ${RELEASE_SEMVER}"
if [[ $release_type == 'prep' ]]; then
  echo "TAG=${TAG_PREFIX}${RELEASE_SEMVER}" > release.env
  echo "DESCRIPTION='Release version ${VERSION} of ${APP}'" >> release.env
  echo "APP=${APP}" >> release.env
  echo "VERSION=${VERSION}" >> release.env
  echo "VERSION_CODE=${VERSION_CODE}" >> release.env
  echo "CURRENT_VERSION=${CURRENT_VERSION}" >> release.env
  echo "VERSION_PATCH=$("$project_dir"/semver.py get-patch)" >> release.env
  echo "VERSION_MINOR=$("$project_dir"/semver.py get-minor)" >> release.env
  echo "VERSION_MAJOR=$("$project_dir"/semver.py get-major)" >> release.env
  echo "BUILD_NUMBER=${BUILD_NUMBER}" >> release.env
  echo "RP_SEMVER_BUILD_REF=${RP_SEMVER_BUILD_REF}" >> release.env
  echo "BUILD=${BUILD}" >> release.env
  echo "RELEASE_SEMVER=${RELEASE_SEMVER}" >> release.env
  echo "----------------release.env--------------------"
  cat release.env
  echo "-----------------------------------------------"
fi

echo "--------------Reference Vars-------------------"
echo "RP_TEMPLATE_NAME: ${RP_TEMPLATE_NAME}"
echo "TAG_PREFIX: ${TAG_PREFIX}"

CURRENT_VERSION_DEPTH=$("$project_dir"/semver.py current-version-depth)
echo "CURRENT_VERSION_DEPTH: ${CURRENT_VERSION_DEPTH}"
echo "-----------------------------------------------"

if [[ $release_type == 'release' && $BUILD -eq 0 ]]; then
  echo "⛔ Build: ${BUILD} is not valid for releases ⛔ "
  exit 1
fi
