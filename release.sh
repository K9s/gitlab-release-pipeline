#!/usr/bin/env bash
set -e

release_type=${1}

commit=${CI_COMMIT_SHA:-$(git rev-parse HEAD)}
branch=${ALLOWED_RELEASE_BRANCH:-$CI_DEFAULT_BRANCH}
project_dir=${CI_PROJECT_DIR:-$(pwd)}

version_file=VERSION

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

# Define some cool release pusher to distinguish from real commits :)
git config user.name "John Glenn"
git config user.email "should.have.been.first@in.space"

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

if [[ $release_type == 'prep' ]]; then
  version_current=$("$project_dir"/version.py get)

  DESCRIPTION="Release version ${version_current} of ${APP}"
  echo "TAG=${APP}-${version_current}" > release.env
  echo "VERSION=${version_current}" >> release.env
  echo "VERSION_MINOR=$("$project_dir"/version.py get-minor)" >> release.env
  echo "VERSION_MAJOR=$("$project_dir"/version.py get-major)" >> release.env
  echo "DESCRIPTION='${DESCRIPTION}'" >> release.env
  echo "APP=${APP}" >> release.env
  echo "----------------release.env--------------------"
  cat release.env
  echo "-----------------------------------------------"
else
  version_current=$("$project_dir"/version.py get-ignore-version-match)

  echo "Bumping version in current branch"
  next_working_version=$("$project_dir"/version.py inc-"${release_type}")

  echo "Pushing new version to ${branch}"
  git add ${version_file}
  git commit -m "Incrementing working version of ${APP} to ${next_working_version}. Prior version was ${version_current}"
  git push origin "${branch}"

  echo "Version $("$project_dir"/version.py get) pushed to ${branch}. Prior version was ${version_current}."
fi
