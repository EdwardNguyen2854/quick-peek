# Quick Peek v0.3 — Document Preview Release

## Release Goal

Add support for document file formats: **doc, docx, xls, xlsx, ppt, pptx, md, txt, html** (PDF already supported).

---

## Formats & Strategy

| Format | Extensions | Strategy |
|--------|-----------|----------|
| **PDF** | `.pdf` | Already supported - direct serving |
| **Word** | `.doc`, `.docx` | Extract text via `python-docx` → render as HTML |
| **Excel** | `.xls`, `.xlsx` | Extract data via `openpyxl` → render as HTML table |
| **PowerPoint** | `.ppt`, `.pptx` | Extract text via `python-pptx` → render as HTML |
| **Markdown** | `.md` | Render to HTML via `markdown` library → serve in iframe |
| **Plain Text** | `.txt` | Serve raw with `text/plain` content type |
| **HTML** | `.html`, `.htm` | Serve raw with `text/html` content type |

### Conversion Approach

For Office formats (doc/docx/xls/xlsx/ppt/pptx), we use **pure Python libraries** instead of LibreOffice:
- `python-docx` for Word documents (docx)
- `openpyxl` for Excel spreadsheets (xlsx)
- `python-pptx` for PowerPoint presentations (pptx)

This approach:
- Requires no system-level installation (unlike LibreOffice)
- Extracts text and tabular data as HTML
- Works cross-platform (Mac, Windows, Linux)

### Preview Architecture

```
File Search → ensure_preview() → format-specific handler
                                 ├── Office formats → python-docx/openpyxl/pptx → HTML → cache → serve
                                 ├── Markdown → markdown library → HTML → cache → serve
                                 ├── Text/HTML → direct serve with appropriate content-type
                                 └── existing formats (PDF, DXF, OBJ, STEP) → unchanged
```

---

## File Changes

### Backend
- `config.py` - Add new formats to `SUPPORTED_FORMATS`
- `preview.py` - Add `ensure_preview()` logic for new formats
- `converters/office_to_html.py` - Pure Python converters (python-docx/openpyxl/pptx) → HTML
- `converters/markdown_to_html.py` - Already exists for Markdown

### Frontend
- `types.ts` - Update `SUPPORTED_FORMATS` in frontend
- `ViewerModal.tsx` - Add routing for new viewer types
- New viewer components: DocViewer, MarkdownViewer, TextViewer, HtmlViewer

---

## Dependencies

- **Backend Python packages**:
  - `markdown==3.7` - Markdown to HTML
  - `python-docx==1.1.2` - Word document text extraction
  - `openpyxl==3.1.5` - Excel spreadsheet data extraction
  - `python-pptx==1.0.2` - PowerPoint text extraction

- **System**: None (no LibreOffice or other system-level dependencies)

---

## Acceptance Criteria

1. All 8 formats searchable and previewable
2. Office formats converted via pure Python libraries to HTML
3. Text/Markdown/HTML served with correct content types
4. Preview caching works for converted files
5. Frontend handles all viewer types correctly
6. No regression on existing formats (PDF, DXF, OBJ, STEP)
7. App starts normally without any system-level dependencies

---

## Team Assignments

- **Astra-architect**: Finalize architecture decision (pure Python approach)
- **Orion-dev**: Implement backend preview pipeline
- **Lyra-designer**: Design frontend viewer components
- **Rigel-review**: Review all code changes
- **Atlas-docs**: Document decisions in `.agents/docs/`
- **Sirius-research**: Validate Python library approach