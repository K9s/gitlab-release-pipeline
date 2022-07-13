# Release-Pipeline

## Overview

The Release Pipeline (RP) is intended to provide the structure needed to define the CI/CD aspects of a modern SDLC.

The general goals of the RP are that it be...

1) Full-featured ... Include all important aspects a software delivery CI/CD ready to be extended/defined
2) Simple (and hopefully obvious) to implement and use
3) Consistent
4) Flexible
5) Solve common problems like semver and pipeline structure

To these ends RP is `Opinionated in form but not in action` meaning that while it does define expectations around jobs,
ordering and general structure it does not 'do' anything by default. The actions around how to build, test, publish,
deploy etc... are fully defined by the pipeline/template authors.

The RP should behave in expected ways and as described in this document. If a behavior is NOT expected please submit an
issue.

## CI/CD and SDLC Concepts

### [Semver](https://semver.org/)

From ^

```
Given a version number MAJOR.MINOR.PATCH, increment the:

MAJOR version when you make incompatible API changes,
MINOR version when you add functionality in a backwards compatible manner, and
PATCH version when you make backwards compatible bug fixes.

Additional labels for pre-release and build metadata are available as extensions to the MAJOR.MINOR.PATCH format.
```

The release pipeline considers major.minor.patch+build in it's semver handling. See [`RP_BUMP` variable](TODO) for more
details.

Ideally semver should be handled automatically or at least in an automated manner. This is especially true for
PATCH versions where the act of 'releasing' a particular version should automatically result in a 'bump' of version.

RP handles Semver via [semver.py](TODO) which is primarily used by the [`set:version`](TODO) job to determine
current version, set version to release (the bump) and does various checks to ensure the version to be built/released
is valid.

All versioning is handled via git tags and the results of `set:version` are available to any job via environment
variables via needs (see [Environment Variables](TODO) and [DAG](TODO) sections below for more details)

The RP also includes jobs to automate [major](TODO), [minor](TODO) and [patch](TODO) semver bumps as well as
support for passing arbitrary version via a pipeline variable. This functionality is disabled by default see
[RP_SEMVER_BUMP_JOBS_DISABLED](TODO) variable for more details.

### Job

A job is named execution of a task or set of tasks that produce some effect or artifact(s). Jobs in
gitlab are configured via yml and the format is defined in the
[.gitlab-ci.yml keyword reference](https://docs.gitlab.com/ee/ci/yaml/gitlab_ci_yaml.html).

In simple terms a job is a place where a script can be executed.

The release pipeline defines a set of jobs and a framework of conventions that make building complete pipelines
'batteries included' and hopefully quicker and less arduous for teams/devs.

See [Core Concepts](TODO) below for more description of 'what' is provided.

### Pipeline

A pipeline is a collection of jobs that accomplish a goal. A goal of the RP is to provide a framework to
facilitate the release of software without teams needing to build out a complete pipeline(s) from scratch.

The RP attempts to solve the problems inherent in building a fully featured pipeline that does all the
things that a modern SDLC needs while remaining simple to implement. The interface that teams need to interact and
therefor the resulting `.gitlab-ci.yml` should be relatively obvious in-use and have minimal 'boiler-plate'.

Fundamentally a software release SDLC has standard actions that need or should occur. The release pipeline provides
an `opinionated in form but not in action` implementation of those actions with sufficient flexibility to remain agile
to the needs of software engineering teams.

### Artifacts

An artifact is a referencable output of a process that can be consumed as needed to do useful work or provide context.

Examples of artifacts are .env files, /dist folders, html reports, really anything can provide value to humans or
other jobs in a pipeline.

In gitlab an artifact can be anything. Artifacts of a job can be consumed as 'needs' by other jobs. This allows
for workflows like a `build` job producing a binary artifact which is then packaged and pushed to a package registry
via a `publish` job. Similarly `test` jobs could consume the same artifact to run unittests, performance tests etc...

Gitlab also has many special purpose artifacts
called [reports](https://docs.gitlab.com/ee/ci/yaml/artifacts_reports.html) that are consumed by Gitlab to enrich
the interface or provide additional functionality. For example junit xml reports for unittest results, coverage reports,
.env for passing environment variables and more.

### Environment [Variables](https://docs.gitlab.com/ee/ci/variables/predefined_variables.html)

The environment that a script executes in defines what kinds of information is available. See ^ for all the
predefined variables that gitlab provides. Environment variables can come from other sources as well.

- CI/CD variables including from Gitlab instance, Gitlab group and Gitlab project
- Pipeline variables
- Needs/dependencies from other jobs... for example `set:version` provides a standard set of variables that allow
  jobs to know what the version and other important context
- The execution context of the runner ie k8s pod, machine with runner deployed etc...

### [Directed Acyclic Graph (DAG)](https://docs.gitlab.com/ee/ci/yaml/#needs)

Jobs in Gitlab live in a stage and by default all jobs in a stage execute in parallel. Stages do not begin
execution until jobs from prior stage has completed.

This works but there often times when jobs in a future stage _should_ be able to start early if there are no
dependencies. Gitlab handles this with 'needs'. A need is a way mark jobs as part of the
[DAG](https://en.wikipedia.org/wiki/Directed_acyclic_graph). Jobs with 'needs' do
not depend on stage ordering. The DAG can be visualized a couple different ways in the UI and can be a valuable way to
understand the flow of a pipeline. A job can have a need on any job in the current stage or prior stage. As the name
implies if there are any _circular dependencies_ that DAG will **become invalid and fail to generate a pipeline**.

The RP makes extensive use of `needs` for almost all jobs (except Gates, see below). Needs generally* define which jobs
will have their artifacts pulled. This means that a `test` job will have a need on the associated `build` so the build
artifact can be tested/used by the test job.

* Note that Gitlab also has the concept of 'dependencies' that define which jobs to pull artifacts from.

## Core Concepts

The following concepts are the core to what release pipeline is and what it implements as a framework. Not all of
these concepts will be needed by all pipelines (and most can be disabled if not neede), but they are all implemented 
to work well together, share similar patterns. A core aim of RP is that it will 'do the right thing' and work 
'in expected ways'. Teams should be able to rely on the functionality of the pipeline without 'weirdness'. If anything
behaves in ways that are outside expectations and/or not documented here please report an issue.

Also, while it might be edifying to understand exactly how each job works the _interface_ (as defined in this
document) is the critical path for teams to make productive use of the capabilities of Release Pipline.

### Gates

Gates are simply a job with a `gate:` prefix that has no 'needs'. They will not trigger until **all** jobs in prior
stages are either skipped, successful or fail but are set to allow failure. In other words they ignore the DAG and
rely on default behavior of stage-based execution ordering.

Gates come in two flavors, manual and automatic.

Manual gates require intervention by a user to hit the 'play' button.
See [`gate:prod`](TODO) and [`gate:release`](TODO) below for more details.

Automatic gates are mostly flow control to ensure that at certain points all prior stage jobs are complete. See DAG
section above for why this is needed. Jobs that should not execute until a particular gate is passed will have a
'need' set for that gate.

Gate jobs are not directly configurable though limited behavior change can be set via variables for example enabling
continuous deployment turns all manual gates to automatic.

See gate job details below for more in-depth descriptions of certain gates such as `gate:release`

### `Lint`

Linting is generally* a static analysis of code that should occur very early in a pipeline and checks for common issues
that does not require 'building'. Examples of linters are Flake8, lint, JSLint and ESLint.

Including a quality linter in a pipeline is recommended to assist in the maintenance of code quality and act as an
early signal of easy-to-fix problems.

* there are exceptions to not requiring builds to do linting however this is the general case. RP is capable of
  handling either case.

### `Build`

A build is the compilation, construction or generation of potentially releasable artifacts and/or artifacts that allow
for the validation of a release.

A build should produce an artifact that is syntactically correct or fail. A build **should not** test that the
artifact is valid. ie no tests should be run other than what is needed to prove the integrity of the artifact (such
as linking, validating signatures etc...)

The build process should be as efficient as is reasonable and strategies such as optimizing build tasks, making use
of cache and eliminating tasks that do not directly assist in the production of a build artifact should be carefully
examined. A build should NOT do anything other than produce an artifact; for example publishing a package
should be left to `publish` jobs.

### `Test`

A test is the validation that an artifact is fit for function and _could_ be released.

`test` jobs have 'needs' on `build` jobs and therefor get the artifact that builds produce.

Unittests are the typical example of the kinds of tasks that `test` jobs should represent. Similar to builds care
should be taken to ensure that the test tasks are as efficient as possible. If at all possible do NOT
'build' anything as doing so during testing invalidates the already built artifact.

In an ideal state, post test stage, there should be high confidence that the artifact __could__ be released.  
RP does support continuous deployment via [RP_ENABLE_CONTINUOUS_DEPLOYMENT](TODO) which turns all manual gates to 
automatic which means that releases happen without human intervention.

### `Publish`

Publishing an artifact means putting that artifact somewhere that it _may_ be consumed outside CI/CD. This can mean
packaging an artifact then submitting it to a package repository like PyPI, tagging a Docker container with version
tags and pushing into a container registry or even updating a document store with generated docs.

The RP has two 'kinds' of publishing that are often configured exactly the same but serve different
purposes.

Prerelease: Publishes non-candidate artifacts ie prerelease or debug that are intended for internal use only. These
artifacts can be used for testing, integration, or deployment to non-prod environments.

Release: Publishes candidate artifacts that are intended for general use. These artifacts can be used for any
purpose and can be deployed to all environments.

### `Integration`

Integration is the act of triggering validation that an artifact can be used by dependencies.

Currently, the RP does not have a full-featured implementation other than an
opt-in job called [`integration:trigger`](TODO)

Some examples where integration could be used.

- Triggering a performance test pipeline in another project
- Triggering a QA test suite pipeline in another project
- Triggering a release pipeline for all known dependencies (which could result in releases of those dependencies
  when a library is updated)
- Update to feature-flags, slack notifications etc....

### `Release`

A release is the act of taking an artifact, associating it to a particular version and making it available for use.
This includes publishing for general use and creating a Gitlab Release (which creates git tag for the version). A
[gate](TODO) ensures that releases are intentional.

An artifact that has been released 'owns' the version it was built and tested as. Once a release has occurred there
is no 'easy' or automated way to take it back. There is always a way but care should be taken when releasing.
It is usually easier to simply kick off another pipeline run which will build toward the next patch version.

### `Deploy`

A deployment is when an artifact is put into a particular environment for use. Not all pipelines will need the
concept of a deployment, for example a python library or docker container.

Similar to publishing, deploys have three 'kinds' that are often configured exactly the same but serve different
purposes.

- Dev: Deployment into environment that use used for adhoc testing and generally looked at by few people
- Preprod: Deployment into environment that is used for final testing before deployment into production. Many people
  may use and validate software deployed here. Examples of these environments are 'staging', 'beta', 'integration'
- Prod: Deployment into environment that actual users can exercise. A gate ensures that deployment into production is
  intentional.

## Stages

RP Stages are defined in [stages.yml](core/stages.yml)

A [visual](docs/stages-overview.png) reference

- precondition: Handle jobs such as `set:version` and version bumping `bump:*`
- prebuild: Do any prebuild jobs like `lint:check` and `gate:preconditions`
- build: Do build jobs such as `build:*`
- postbuild: Unused by default, available for [Arbitrary Jobs](TODO)
- pretest: Unused by default, available for [Arbitrary Jobs](TODO)
- test: Run tests jobs such as `test:*`
- posttest: Unused by default, available for [Arbitrary Jobs](TODO)
- prerelease: `gate:prerelease` to ensure all test jobs are complete and `publish:prerelease`, `publish:debug` jobs
- dev: Deploy `deploy:dev`
- accessibility: Unused by default, available for [Arbitrary Jobs](TODO)
- integration: Final integration testing before release. Includes jobs like `integration:trigger`
- release: Jobs that effectuate a 'release' this includes jobs like `gate:release`, `gitlab:release` and
  `publish:release`
- postrelease: jobs like `set:stable:tag`
- preprod: Deploy `deploy:preprod`
- prod: Do production deploy ala `deploy:prod`
- wrapup:

## Core Jobs

TODO

### Release vrs non-release jobs

TODO

### Naming convention

TODO

### Preconditions

TODO

#### `set:version`

TODO

### `gate:preconditions`

TODO

```
TAG=
SEMVER=
VERSION=
VERSION_CODE=
CURRENT_VERSION=
VERSION_MINOR=
VERSION_MAJOR=
DESCRIPTION=
BUILD_NUMBER=
RP_TEMPLATE_NAME=
APP=
```

#### `bump:major`

TODO

#### `bump:minor`

TODO

#### `bump:patch`

TODO

### Lint

TODO

```
LINT_JOB=
```

#### `lint:check`

TODO

### Build

TODO

```
BUILD_JOB=
PRE_RELEASE=
```

#### `build:debug`

TODO

#### `build:prerelease`

TODO

#### `build:candidate`

TODO

### Test

TODO

```
TEST_JOB=
PRE_RELEASE=
```

#### `test:debug`

TODO

#### `test:prerelease`

TODO

#### `test:candidate`

TODO

### Publish

TODO

```
PUBLISH_JOB=
```

#### `publish:debug`

TODO

#### `publish:prerelease`

TODO

#### `publish:candidate`

TODO

### Release

TODO

#### `gitlab:release`

TODO

#### `set:stable:tag`

TODO

### Deploy

TODO

```
DEPLOY_JOB=
PRE_RELEASE=
```

#### `deploy:dev`

TODO

#### `deploy:preprod`

TODO

#### `deploy:prod`

TODO

### Deploy Stop

TODO

#### `deploy:dev:stop`

TODO

#### `deploy:preprod:stop`

TODO

#### `deploy:prod:stop`

TODO

### Integration

TODO

#### `integration:trigger`

TODO

### Gates

TODO

#### `gate:prerelease`

TODO

#### `gate:release`

TODO

#### `gate:dev`

TODO

#### `gate:preprod`

TODO

#### `gate:prod`

TODO

## Core Templates

TODO

### core

TODO

### docker-build

TODO

### docker-python

TODO

### docker-run

TODO

### package-python

TODO

### script-python

TODO

## Customization

Customization of core jobs is via configuration of `.core:jobs` (dot prefixed jobs or extension points) and by setting 
variables.

### Extension Points

Every core job is configured via extension points. Final job configuration is a result of gitlab
[extends](https://docs.gitlab.com/ee/ci/yaml/#extends) that pull together these extension points.
Extension point jobs are prefixed with a `.` and their name shadows the job that will be extended by them.

Direct modification of `core:jobs` should **be avoided**.... use extension points only. It is considered a bug if
direct modification of a job is needed. The exception being [Replacing jobs](TODO).

More specific extension points supersede less specific extension points meaning they can override fields. For
example, you can define generally how a build occurs in `.build` but have a more specific definition for `.build:debug`

#### Available Extension Points

- `.base`
- `.lint`, `.lint:check`
- `.build`, `.build:debug`, `.build:candidate` `.build:prerelease`, `.build:override`
- `.test`, `.test:debug` `.test:candidate`, `.test:prerelease`, `.test:override`
- `.publish`, `.publish:prerelease` `.publish:debug`, `.publish:candidate`, `.gitlab:release`, `.publish:override`
- `.deploy`, `.deploy:dev`, `.deploy:preprod`, `.deploy:prod`, `.deploy:override`
- `.deploy:stop`, `.deploy:dev:stop`, `.deploy:preprod:stop`, `.deploy:prod:stop`
- `.integration`, `.integration:trigger`

### Overrides

Overrides are an escape valve and should only be used where the additive nature of extends will not work. Generally
this can occur when there is a field in a job that is a list type and the user needs its value set for an entire type
of job but doing so has no effect. An example; setting 'needs' via the `.test` extension point will be ignored.

This behavior is due to order that jobs are extended and where the default set of 'needs' come from.  
Needs is a list type field and gitlab does not merge lists. Needs for core jobs are defined in the more specific dot
job (ie `test:debug`) due to each job having different need targets (ie `test:debug` needs `build:debug` but not
`build:candiate`). To solve this problem you either duplicate your configuration for every `test:*` job in your
pipeline _or_ use an override extension point.

Overrides are simply an extension point that is the last to extend the final job meaning anything set will take
precedence. Note that doing this for 'needs' will break the default needs defined and may lead to unexpected
ordering due to the DAG changing.

Available overrides `.build:override`, `.test:override`, `.publish:override`, `.deploy:override`

### Feature Flags/Variables

Features of the RP can also be controlled via variables. _most_ variables have an `RP_` prefix.  
_Generally_ these variables have defaults that _should work_. Don't change/set variables unless needed to
accomplish a specific outcome/goal.

#### Core

TODO

```
#VERSION:
#BUILD_NUMBER:
DIR: src
#APP:
#RP_TAG_PREFIX: "{self.app}-"
RP_GITLAB_RELEASE_PREFIX: '[Release]'
```

#### Capabilities

TODO

```s
#RP_CENTRAL_REGISTRY_PROJECT_ID:
#RP_LINT_DISABLED:
#RP_INTEGRATION_TRIGGER_ENABLED:

#RP_BUILDS_DISABLED:
#RP_CANDIDATE_BUILD_DISABLED:
#RP_DEBUG_BUILD_DISABLED:
#RP_PRERELEASE_BUILD_DISABLED:

#RP_PUBLISH_DISABLED:
#RP_CANDIDATE_PUBLISH_DISABLED
#RP_DEBUG_PUBLISH_DISABLED:
#RP_PRERELEASE_PUBLISH_DISABLED:

#RP_ENABLE_CONTINUOUS_DEPLOYMENT:
#RP_DEPLOYS_DISABLED:
#RP_PRODUCTION_DEPLOY_DISABLED:

#RP_TESTS_DISABLED:
#RP_CANDIDATE_TESTS_DISABLED:
#RP_DEBUG_TESTS_DISABLED:
#RP_DEBUG_TESTS_ENABLED:
#RP_PRERELEASE_TESTS_DISABLED:

#RP_ALLOW_FLAKE8_FAILURE:
#RP_SEMVER_BUILD_REF:
#RP_SEMVER_INCLUDE_BUILD:
#RP_INCLUDE_PRECONDITIONS:
#RP_SEMVER_BUMP_JOBS_DISABLED:
#RP_LATEST_TAGGED_ANCESTOR_IGNORED:
#RP_RC_TAG_FIXUP_SUFFIXES:
```

---

##### _`RP_BUMP`_

Determines what identifier in the SemVer will be considered when deriving 'next_version'. This is also
known as version bumping. The implementation of this handing closely adheres
to [SemVer](https://semver.org/#semantic-versioning-specification-semver).

##### default: patch

##### values: build, patch, minor, major

Common to all:

- `set:version` job will determine if the proposed next_version is a valid target (call can_bump_to() see
  [semver.py](TODO)) which will ensure the version can be bumped to without violating semver rules or conflict
  with existing releases (tags)
- `set:version` will expose `VERSION`, `BUILD_NUMBER` and other envvars for use by build/test/publish jobs later in
  the pipeline. See [`set:version` job](TODO) for more details.
- All versions consider/include `BUILD_NUMBER` as a build identifier

When set to anything other than `build`

- The matching section in the core version is increased by 1
- The build portion (section after '+') is informational only.
- Conflicts will occur if the same core version is encountered and will prevent the pipeline from continuing.
    - ie once semver 1.2.3+20 is released no other 1.2.3 versions can be released regardless of their build number

When set to `major` or `minor`

- The sections to the right of the matching section are 0'd out ie SemVer spec is followed
- ie ``Patch version MUST be reset to 0 when minor version is incremented. Patch and minor versions MUST be reset to
  0 when major version is incremented.``

When set to `build`

- Determining the ‘next_version’ is a direct pass through of the core version (no 'bumping' occurs)
- Check to ensure that the next_version is not older the latest released version uses exact tags rather the core
  version. (build is respected)
- Conflicts will _**not**_ occur so long as the build is greater than the latest published version.
    - ie semver 1.2.3+20 can be released without a new pipeline run of 1.2.3+21 breaking. Attempting to
      kick off a pipeline with an older build will prevent the pipeline from continuing ie 1.2.3+10 will fail.

---

##### Replacing jobs

Certain jobs are extended in such a way that they can be overridden completely to swap in a custom implementation.

###### Overriding `set:version`

###### Overriding `gitlab:release`

#### Internal

TODO

These variables are for internal purposes and/or are set at the Gitlab instance level and do not and should not be
used by pipeline authors.

```
RP_TEMPLATE_NAME: 'core'

#RP_PARENT_PIPELINE_ID:

#RP_SETUP_ARTIFACT_REF:
#RP_SETUP_ARTIFACT_JOB:

#RP_TEMPLATE_PROJECT_API_TOKEN
#RP_TEMPLATE_PROJECT_ID:
#RP_TEMPLATE_PROJECT_NAMESPACE:
#RP_TEMPLATE_PROJECT_NAME:
#RP_BASE_IMAGE:
#RP_IMAGE_TAG:
#RP_RELEASE_BRANCH:
#RELEASE_PASS:
#RELEASE_USER:
```

#### Gitlab

TODO

```
ARTIFACT_COMPRESSION_LEVEL: 'default'
CACHE_COMPRESSION_LEVEL: 'fast'
FF_USE_FASTZIP: 'true'
TRANSFER_METER_FREQUENCY: '5s'
CACHE_REQUEST_TIMEOUT: '20m'
```

### Adding environment variables to job output

All jobs that extend `.base` (`lint:*`, `build:*`, `test:*`, `publish:*`, `deploy:*`) submit
[dotenv reports](https://docs.gitlab.com/ee/ci/yaml/artifacts_reports.html#artifactsreportsdotenv) this allows
dependent jobs to have access to environment variables such as PRE_RELEASE. To augment this capability simply
echo or cat appropriately formatted variables to `$CI_PROJECT_DIR/rp.env`

Note this is accomplished by using [after_script](https://docs.gitlab.com/ee/ci/yaml/#after_script) which means no
configuration should use the 'after_script' field without understanding that dotenv capability will be broken.

examples

```yaml
.publish:
  script:
    - echo "ARTIFACT_URL='google.com'" >> $CI_PROJECT_DIR/rp.env

.build:candidate:
  script:
    - cat $DIR/build.env >>  $CI_PROJECT_DIR/rp.env
```

Note that the content of rp.env is emitted to stdout in every job and will be visible in console output .... no
secrets ;)

Also note that rp.env _should_ always be appended to

### Caching

TODO

### Arbitrary Jobs

TODO

### Development Workflows

TODO

#### Trunk based development

TODO

#### 'Feature Branches'

TODO

#### Merge Requests

TODO

#### Specifying `SEMVER`, `VERSION` and `BUILD_NUMBER` explicitly

### Internals

#### semver.py, release.sh and .config/*

TODO

#### Testing and pipeline validation

TODO

#### Assumptions for templates

TODO

## Roadmap/Next Steps

- Complete writing README.md
