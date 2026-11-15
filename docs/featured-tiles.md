# Featured tiles (T6)

Picked by a script, 2026-11-14, from `moon_pipeline/20261114T023547307090Z_39a681` (region environment scope). Still valid for the current run `20261115T070913357556Z_0070bc`: its Earth matches and terrain classes are identical.

**T6 decided 2026-11-15:** feature three tiles per region: a strong physical match, a high-cosine match with poor physical agreement, and a match outside Atacama. The region page shows them as "Three patches to start with", from `app/src/featured.json`. `npm --prefix app run check:browser` fails if a new export breaks a pick's kind.

## How they were picked

Every pick uses the tile's **rank 1** Earth match, so in the app it is always the top row of that patch's Earth analogs page. Tiles where Hanxi's CNN disagrees with the direct slope rule were left out, because they need extra explanation on stage.

| Kind | Rule |
| --- | --- |
| Strong match | Highest cosine among tiles with the most checks in band (5 of 5 in every region) |
| Misleading | Highest cosine with 0 of 5 physical checks in band. Shows why the checks matter |
| Not Atacama | Highest cosine whose best match is not Atacama (Atacama is best for about 88% of tiles, [A4](team-blockers.md)) |

A tile is used only once per region, so a later kind falls back to the next best tile.

## Tiles

Open a patch at `#/region/<region>/patch/<patch>`. The environment scores are the same for every tile in a region (region scope), so they don't separate tiles.

### Leibnitz Beta Plateau (`leibnitz-beta-plateau`)

| Kind | Patch | Rank 1 Earth match | Cosine | Checks in band | Rover | On foot |
| --- | --- | --- | --- | --- | --- | --- |
| Strong match | `r448-c480` | Atacama | 0.992 | 5 of 5 | operable | easy |
| Misleading | `r192-c192` | Wadi Rum | 0.969 | 0 of 5 | operable | caution |
| Not Atacama | `r320-c480` | Death Valley | 0.992 | 3 of 5 | operable | easy |

### Malapert Massif (`malapert-massif`)

| Kind | Patch | Rank 1 Earth match | Cosine | Checks in band | Rover | On foot |
| --- | --- | --- | --- | --- | --- | --- |
| Strong match | `r320-c480` | Atacama | 0.988 | 5 of 5 | operable | caution |
| Misleading | `r128-c384` | Wadi Rum | 0.982 | 0 of 5 | non-operable | unsuitable |
| Not Atacama | `r96-c384` | Wadi Rum | 0.975 | 0 of 5 | non-operable | unsuitable |

### de Gerlache–Kocher Massif (`de-gerlache-kocher-massif`)

| Kind | Patch | Rank 1 Earth match | Cosine | Checks in band | Rover | On foot |
| --- | --- | --- | --- | --- | --- | --- |
| Strong match | `r256-c608` | Atacama | 0.990 | 5 of 5 | operable | easy |
| Misleading | `r480-c96` | Atacama | 0.985 | 0 of 5 | marginal | unsuitable |
| Not Atacama | `r224-c288` | Death Valley | 0.995 | 4 of 5 | operable | easy |

### Haworth (`haworth`)

| Kind | Patch | Rank 1 Earth match | Cosine | Checks in band | Rover | On foot |
| --- | --- | --- | --- | --- | --- | --- |
| Strong match | `r544-c544` | Atacama | 0.998 | 5 of 5 | operable | easy |
| Misleading | `r512-c480` | Atacama | 0.976 | 0 of 5 | operable | easy |
| Not Atacama | `r544-c160` | Wadi Rum | 0.997 | 4 of 5 | operable | easy |

### Faustini Rim A (`faustini-rim-a`)

| Kind | Patch | Rank 1 Earth match | Cosine | Checks in band | Rover | On foot |
| --- | --- | --- | --- | --- | --- | --- |
| Strong match | `r192-c64` | Atacama | 0.996 | 5 of 5 | operable | easy |
| Misleading | `r320-c128` | Atacama | 0.969 | 0 of 5 | marginal | unsuitable |
| Not Atacama | `r32-c192` | Death Valley | 0.995 | 5 of 5 | operable | easy |

### de Gerlache Rim 2 (`de-gerlache-rim-2`)

| Kind | Patch | Rank 1 Earth match | Cosine | Checks in band | Rover | On foot |
| --- | --- | --- | --- | --- | --- | --- |
| Strong match | `r128-c224` | Atacama | 0.993 | 5 of 5 | operable | easy |
| Misleading | `r64-c480` | Atacama | 0.977 | 0 of 5 | marginal | unsuitable |
| Not Atacama | `r544-c128` | Death Valley | 0.998 | 2 of 5 | operable | easy |

### Connecting Ridge Extension (`connecting-ridge-extension`)

| Kind | Patch | Rank 1 Earth match | Cosine | Checks in band | Rover | On foot |
| --- | --- | --- | --- | --- | --- | --- |
| Strong match | `r320-c448` | Atacama | 0.989 | 5 of 5 | operable | caution |
| Misleading | `r32-c608` | Wadi Rum | 0.985 | 0 of 5 | non-operable | unsuitable |
| Not Atacama | `r160-c544` | Death Valley | 0.984 | 4 of 5 | operable | easy |

## Suggested demo path

1. **Haworth `r544-c544`.** Cosine 0.998, 5 of 5 checks in band, rover operable and on foot easy. The best case.
2. **Malapert Massif `r128-c384`.** Cosine 0.982 to Wadi Rum but 0 of 5 checks in band, and rover non-operable. A high cosine alone is not enough.
3. **de Gerlache–Kocher Massif `r224-c288`.** Cosine 0.995 to Death Valley, so Atacama isn't the only answer.
4. Then the environment page for the same region, and the upload.
