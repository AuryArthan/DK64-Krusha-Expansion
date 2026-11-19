# Offline placement atlas

Build either atlas from the repository root with your original USA ROM in `rom/dk64.z64`.

```sh
/usr/bin/python3 tools/build-map-atlas.py --out runtime/atlas-campaign
/usr/bin/python3 tools/build-recruitment-atlas.py --out runtime/atlas-keys
```

Open `runtime/atlas-campaign/index.html` for the campaign or `runtime/atlas-keys/keys.html` for the five recruitment keys. Each generator reads local ROM geometry and writes a self-contained atlas. Choose a fresh output directory for a new study.

Map A lets you move a Krusha marker or enter precise X/Y/Z coordinates. The height filter and rotatable view C help distinguish overlapping floors. Original pickups, warps and shop entrances are landmarks. Edit **Challenge / access notes** to describe a support, approach or intended route. Export the JSON to keep or share a revision. A marker’s Y coordinate should be checked against the actual terrain or object that supports it.

For the campaign, apply the reviewed changes to matching pins or world entries in the [campaign file](../../data/placements/campaign.json). For a key export, run the following command and compare the result to the [runtime key file](../../data/placements/recruitment-keys.json). The converter verifies owner, map and identity, and writes a new file for review.

```sh
/usr/bin/python3 tools/import-recruitment-keys.py --input YOUR_EXPORT.json --out runtime/reviewed-keys.json
```

A browser edit takes effect in game after you transfer the coordinates to the source, rebuild, and load the new ROM. [First collectible walkthrough](../../CONTRIBUTING.md)
