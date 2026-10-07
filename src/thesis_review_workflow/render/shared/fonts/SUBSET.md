# Vendored font subset

Noto Sans Regular, Bold, Italic and Bold Italic (SIL OFL 1.1, see `LICENSE-OFL`;
the family has no Reserved Font Name), subset with fontTools 4.46 from the
Debian `fonts-noto-core` files so every packaged workflow tool stays small:

```text
python3 -m fontTools.subset NotoSans-<Style>.ttf --output-file=NotoSans-<Style>.ttf \
  --unicodes="U+0020-007E,U+00A0-017F,U+0218-021B,U+02C6-02DD,U+0391-03C9,U+2000-206F,U+20AC,U+2122,U+2190-2195,U+21D2,U+21D4,U+2208,U+2211,U+2212,U+221A,U+221E,U+2248,U+2260,U+2264,U+2265,U+FFFD"
```

The range covers Czech and Western European Latin, typographic punctuation,
Greek letters, arrows, and common relational operators. A character outside it
falls back to whatever font Typst finds, so widen the range here rather than
adding a second family.
