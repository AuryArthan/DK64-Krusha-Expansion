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
asset_field() {
  local name=$1 field=$2
  gh api "repos/$repo/releases/$id/assets" --paginate \
    --jq ".[] | select(.name == \"$name\") | .$field"
}
actual=$(asset_field "$asset" digest)
if [[ "$actual" != "sha256:$digest" ]]; then
  if [[ "$draft" == true ]]; then
    gh release upload "$tag" "$patch" -R "$repo" --clobber
  elif [[ "$tag" == v1.0.2 && "$id" == 454685667 && "$digest" == c5e513d084855e8484f69402b22aad1012ce3d9a1d3b3e7ddd59dd0066d8ee5d ]]; then
    # Stage and verify the replacement before retiring the original download.
    original=sha256:49decd1fca4212bb7bbc75843aa8ea3316fdebff0eea65503add384555cce782
    staged="DK64-Krusha-Expansion-${digest:0:12}.bps"
    pending=$(asset_field "$staged" digest)
    if [[ "$actual" == "$original" ]]; then
      if [[ -z "$pending" ]]; then
        scratch=$(mktemp -d)
        trap 'rm -f -- "$notes" "$scratch/$staged"; rmdir -- "$scratch"' EXIT
        cp -- "$patch" "$scratch/$staged"
        gh release upload "$tag" "$scratch/$staged" -R "$repo"
      fi
      [[ $(asset_field "$staged" digest) == "sha256:$digest" ]]
      old_id=$(asset_field "$asset" id)
      [[ "$old_id" =~ ^[0-9]+$ ]]
      gh api --method DELETE "repos/$repo/releases/assets/$old_id" --silent
    elif [[ -n "$actual" || "$pending" != "sha256:$digest" ]]; then
      echo "Unexpected v1.0.2 assets. Inspect the release before retrying." >&2
      exit 1
    fi
    # A retry after deletion can promote the already verified upload.
    staged_id=$(asset_field "$staged" id)
    [[ "$staged_id" =~ ^[0-9]+$ ]]
    gh api --method PATCH "repos/$repo/releases/assets/$staged_id" -f name="$asset" --silent
  else
    echo "Published $tag has a missing or different BPS. Check its assets." >&2
    exit 1
  fi
  [[ $(asset_field "$asset" digest) == "sha256:$digest" ]]
fi
if [[ "$draft" == true ]]; then
  gh release edit "$tag" -R "$repo" --draft=false --latest
fi
