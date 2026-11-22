#!/usr/bin/env bash
# Runs in the publication repository root on a GitHub-hosted runner.
set -euo pipefail
tag=${1:?supply the release tag}
asset=DK64-Krusha-Expansion.bps
patch="release-assets/$tag/$asset"
repo=AuryArthan/DK64-Krusha-Expansion
case "$tag" in
  v1.0.0) [[ $(git rev-parse "$tag^{commit}") == 2199402915fbbe0463c58a87b7054a2c84f408db ]] ;;
  v1.0.1|v1.0.2) [[ $(git rev-parse "$tag^{commit}") == $(git rev-parse HEAD) ]] ;;
  *) exit 2 ;;
esac
manifest=$(git show "$tag:docs/releases/$tag.json")
[[ $(jq -r .bps_filename <<< "$manifest") == "$asset" ]]
digest=$(jq -er .bps_sha256 <<< "$manifest")
printf '%s  %s\n' "$digest" "$patch" | sha256sum -c -

# Read the approved notes from the tag. GitHub release pages need absolute links.
notes=$(mktemp)
trap 'rm -f -- "$notes"' EXIT
git show "$tag:docs/releases/$tag.md" | sed \
  -e "s|(../../README.md)|(https://github.com/$repo/tree/$tag#readme)|g" \
  -e "s|($tag.json)|(https://github.com/$repo/blob/$tag/docs/releases/$tag.json)|g" > "$notes"

if ! gh release view "$tag" -R "$repo" --json id >/dev/null; then
  gh release create "$tag" -R "$repo" --verify-tag --draft \
    --title "Krusha Expansion $tag" --notes-file "$notes"
fi
metadata=$(gh release view "$tag" -R "$repo" --json databaseId,isDraft)
id=$(jq -er .databaseId <<< "$metadata")
draft=$(jq -r .isDraft <<< "$metadata")
asset_digest() {
  gh api "repos/$repo/releases/$id/assets" --paginate \
    --jq ".[] | select(.name == \"$asset\") | .digest"
}
actual=$(asset_digest)
if [[ "$actual" != "sha256:$digest" ]]; then
  if [[ "$draft" != true ]]; then
    echo "Published $tag has a missing or different BPS. Check its assets." >&2
    exit 1
  fi
  gh release upload "$tag" "$patch" -R "$repo" --clobber
  [[ $(asset_digest) == "sha256:$digest" ]]
fi
if [[ "$draft" == true ]]; then
  gh release edit "$tag" -R "$repo" --draft=false --latest
fi
