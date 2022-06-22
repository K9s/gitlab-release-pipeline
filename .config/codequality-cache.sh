#!/usr/bin/env bash

declare -a StringArray=(
  "codeclimate/codeclimate:0.85.26"
  "codeclimate/codeclimate-eslint"
  "codeclimate/codeclimate-structure"
  "codeclimate/codeclimate-duplication"
  "codeclimate/codeclimate-rubocop:rubocop-0-92"
  "codeclimate/codeclimate-csslint"
  "codeclimate/codeclimate-fixme"
)

for image in ${StringArray[@]}; do
   docker pull registry.${CI_SERVER_HOST}/ci/registry/${image} || docker pull ${image}
   docker tag registry.${CI_SERVER_HOST}/ci/registry/${image} ${image} || true
   docker tag ${image} registry.${CI_SERVER_HOST}/ci/registry/${image}
   docker push registry.${CI_SERVER_HOST}/ci/registry/${image}

   echo "${image} updated and pushed to registry"
done

echo "All done!!! Code quality should be ready to go!"
