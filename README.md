# Marmont cipher — final solution package

AI assistance: **GPT-6 Astra and Claude**.

Open **START_HERE.html** for the source plate, full French and English reading, row-by-row decoding, searchable glyph key, and remaining sign alternatives. The page works directly from the extracted folder without a server or account.

This package reproduces the final proposed solution from its supplied transcription, key, editorial inputs, and source-image coordinates. The key is an input to reproduction. The raw decoding and the editorial reading remain separate so every restoration can be inspected.

## Verify and reproduce

Use Python 3.10 or later. From this extracted directory:

```sh
python3 -m pip install -r requirements.txt
python3 verify.py
python3 reproduce.py
```

Use `python` in place of `python3` if that is your installation's command. Pillow is the only third-party Python dependency. Installation can require a network; verification and reproduction run offline and need no model access or API keys.

`verify.py` checks the distributed-file hashes, complete key/transcription coverage, all 29 editorial interventions, every glyph and source crop, and the offline page's local links. A failed check returns a nonzero exit code.

`reproduce.py` writes a fresh generated edition to **results/reproduced/**: the literal text, editorial reading and alignment, all 155 glyphs and their raw/context companions, the contact sheet, all unit and row crops, and a new offline reading page. Its copied inputs and source images allow the generated page to be read independently.

For the standard-library checks without installing Pillow:

```sh
python3 verify.py --text-only
python3 reproduce.py --text-only
```

Those commands explicitly omit image verification/reconstruction. Use the default commands for the complete check. The recorded package validation is in **VERIFICATION.json**.

## Files

| Path | Contents |
|---|---|
| solution/ | Literal decoding, editorial French and English, and 24-row alignment. |
| inputs/ | Final key and token stream; reading and intervention inputs; complete unit coordinates/evidence categories; uncertainty and defect records; source comparisons; glyph extraction rules. |
| sources/ | Supplied cipher plate and printed Napoleon correspondence page, with original bytes retained. |
| glyphs/ | 155 PNG glyphs, 155 raw grayscale companions, 155 wider source contexts, a contact sheet, and label-to-file metadata. |
| views/ | Source-pixel crops of all 1,310 units and all 24 rows. |
| scripts/ | Portable final-artifact generation and verification code. |
| METHODS.md | Exact transformation rules, coordinate conventions, evidence categories, and interpretation limits. |
| SOURCES.md and CREDITS.md | Source citations and author/AI credits. |
| SHA256SUMS | Hashes for every distributed file except the manifest itself. |

The body contains **1,300 cipher units plus ten visible cleartext letters** and **155 distinct cipher labels**. TARGET remains unresolved in the literal text. Forty-eight labels have contextual or otherwise limited evidence; six retain explicit alternative readings. The package includes those qualifications with the final result.

The successful checks establish that the supplied inputs reproduce the distributed solution consistently. Historical attribution, unique sign values, and manuscript authenticity remain subject to the stated evidence limits in METHODS.md.
