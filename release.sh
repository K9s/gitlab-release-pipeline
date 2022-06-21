#!/usr/bin/env bash
set -e

release_type=${1}

commit=${CI_COMMIT_SHA:-$(git rev-parse HEAD)}
branch=${ALLOWED_RELEASE_BRANCH:-$CI_DEFAULT_BRANCH}

if ! git branch -a --contains "${commit}" | grep -e "^[* ]*remotes/origin/${branch}\$"
then
  echo -e "###\n### Not on ${branch}. Only the branch defined by ALLOWED_RELEASE_BRANCH can be released.\n###"
  exit 1
else
  echo -e "###\n### Release ${release_type} for ${commit} on ${branch}\n###"
fi

if [[ -z "${APP}" ]]; then
  # shellcheck disable=SC2016
  echo '$APP is unset deriving from folder name'
  app=$(basename $(realpath .))
  if [[ $app == 'src' ]]; then
    app=$(basename $(realpath ../))
  fi
  export APP=$app
fi

# Work around the limitation where gitlab runners can't push to repos.
if [[ -z "${RELEASE_USER}" ]]; then
  echo "Using default checkout credentials"
  echo "  if push fails create an access token with repository write"
  echo "  and set RELEASE_USER and RELEASE_PASS variables"
else
  echo "Using credentials from RELEASE_USER: ${RELEASE_USER}"
  GIT_URL=$(git remote get-url origin)
  GIT_URL=$(echo "$GIT_URL" | sed -r "s/^(.+?\/\/)(.+?):(.+?)@(.+)$/\1${RELEASE_USER}:${RELEASE_PASS}@\4/")
  git remote set-url origin "$GIT_URL"
fi

git checkout "${branch}"
echo "Fetching from origin"
git fetch -f || true
git fetch -f --tags || true

project_dir=$(dirname "$0")

echo "Determining version using RP_TAG_PREFIX: ${RP_TAG_PREFIX:-'default'}"
export __APP=`echo "$APP" | tr '-' '_'`
_APP=$(python -c "import os;print(os.environ.get('__APP').upper())")
VERSION_CODE=$((${_APP}_VERSION_CODE+1))
BUILD_NUMBER="${BUILD_NUMBER:-$CI_PIPELINE_IID}"
RP_SEMVER_BUILD_REF=${RP_SEMVER_BUILD_REF:-BUILD_NUMBER}
export BUILD=$((${RP_SEMVER_BUILD_REF}))
TAG_PREFIX=$("$project_dir"/semver.py get-tag-prefix)
VERSION=$("$project_dir"/semver.py get)
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
  echo "VERSION_MINOR=$("$project_dir"/semver.py get-minor)" >> release.env
  echo "VERSION_MAJOR=$("$project_dir"/semver.py get-major)" >> release.env
  echo "BUILD_NUMBER=${BUILD_NUMBER}" >> release.env
  echo "RP_SEMVER_BUILD_REF=$RP_SEMVER_BUILD_REF" >> release.env
  echo "BUILD=${BUILD}" >> release.env
  echo "RELEASE_SEMVER=${RELEASE_SEMVER}" >> release.env
  echo "RP_TEMPLATE_NAME=${RP_TEMPLATE_NAME}" >> release.env
  echo "----------------release.env--------------------"
  cat release.env
  echo "-----------------------------------------------"
fi
