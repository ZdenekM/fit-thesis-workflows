# PDF Detail Layer

This repository keeps `pdftotext -layout` extraction as the stable default
evidence path for thesis review. Use `pdf-reader-mcp` only as an optional detail
layer when text extraction is not enough.

## Setup

`pdf-reader-mcp` currently requires Node.js 22 or newer. Add it to Codex with:

```bash
codex mcp add pdf-reader -- npx @sylphx/pdf-reader-mcp
```

If the MCP server is not installed or cannot read a file, continue with the
available `pdftotext` extract and record the limitation. Absence of the MCP
server is not a blocker for ordinary text review.

## When To Use It

Use the PDF detail layer for targeted checks only:

- metadata, page count, and document structure,
- specific page ranges when evidence needs page-level precision,
- figures, tables, captions, and layout-sensitive claims,
- cases where `pdftotext` output is ambiguous or loses important formatting,
- literature PDFs where the relevant evidence is in a figure, table, equation,
  or page-local passage.

Do not use it as a routine replacement for text extraction. Do not require OCR
for V1; expected thesis and paper inputs are text-based PDFs.

## Privacy

Never write student PDFs, downloaded papers, extracted text, screenshots, or
derived PDF evidence to tracked repository paths. Put all case-specific PDF
inputs, literature PDFs, metadata cache, and working notes under the ignored
`cases/<case-id>/` workspace.

When student-facing feedback mentions page/layout evidence, it must be based on
a concrete PDF check. If only plain text extraction was used, phrase findings as
text-extract evidence rather than page/layout evidence.
