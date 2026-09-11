# Bundled PDF fonts

Noto Sans Regular and Bold are distributed unchanged under the SIL Open Font
License 1.1 in `LICENSE`. They provide embedded Cyrillic glyphs without relying
on fonts installed on the Vercel host. Do not replace them with proprietary
Windows fonts.

Official upstream: https://github.com/notofonts/noto-fonts

Pinned source revision: `ffebf8c1ee449e544955a7e813c54f9b73848eac`

- `hinted/ttf/NotoSans/NotoSans-Regular.ttf`
  - SHA-256: `b85c38ecea8a7cfb39c24e395a4007474fa5a4fc864f6ee33309eb4948d232d5`
- `hinted/ttf/NotoSans/NotoSans-Bold.ttf`
  - SHA-256: `c976e4b1b99edc88775377fcc21692ca4bfa46b6d6ca6522bfda505b28ff9d6a`

These files must be included in the Python function deployment bundle at
`server/assets/fonts/`. The PDF renderer does not download fonts at runtime.
