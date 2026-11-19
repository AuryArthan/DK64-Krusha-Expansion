# Portrait, title and voice assets

| To change | Source and build step |
| --- | --- |
| Barrel portrait, menu face and startup silhouette | Run `/usr/bin/python3 tools/prepare-krusha-portrait.py YOUR_SQUARE_RGBA.png`, then rebuild. The converter derives the 64×64 portrait and replaces Krusha’s silhouette in the six-head lineup. Its optional `--gray` also changes the identity color read from that lineup. |
| Shout counter portrait | Edit `krusha/hud/krusha-shout-source.png`. The build reduces its content to 48×48 inside the native 64×64 sprite and encodes both texture halves. |
| Intro credit and expansion title logo | Edit the source PNGs in `intro/`. The builder prepares the game textures and places them in the existing intro and title slots. |
| Primitive Roar recording | Run `./tools/setup-vadpcm.sh`, then `/usr/bin/python3 build/prepare_scream.py YOUR_STEREO.wav` and rebuild. Regeneration uses FFmpeg and the VADPCM encoder. An ordinary build uses the committed recording, encoded stream and codebook. |

Each portrait and the voice payload has provenance or checksum metadata beside the source. When supplying replacement media, document its author and applicable terms. [License scope](../LICENSE.md)
