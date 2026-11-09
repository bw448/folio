# Third-Party Notices

Folio is licensed under **AGPL-3.0**. It depends on the following
open-source projects and data sources. Their licenses apply to their own code
and data; this file is attribution, not a replacement for their license texts.

## Runtime dependencies

| Project | License | Use |
| --- | --- | --- |
| [PyMuPDF](https://github.com/pymupdf/PyMuPDF) | AGPL-3.0 or commercial | PDF/EPUB rendering, reflow, text coordinates, bilingual PDF |
| [FastAPI](https://github.com/fastapi/fastapi) | MIT | HTTP API |
| [Uvicorn](https://github.com/encode/uvicorn) | BSD-3-Clause | ASGI server |
| [Pydantic](https://github.com/pydantic/pydantic) | MIT | Request models |
| [httpx](https://github.com/encode/httpx) | BSD-3-Clause | HTTP client |
| [python-multipart](https://github.com/Kludex/python-multipart) | Apache-2.0 | File uploads |
| [NumPy](https://github.com/numpy/numpy) | BSD-3-Clause | OCR numerical work |
| [RapidOCR](https://github.com/RapidAI/RapidOCR) | Apache-2.0 | Offline OCR |
| [ONNX Runtime](https://github.com/microsoft/onnxruntime) | MIT | OCR inference |
| [OpenCV](https://github.com/opencv/opencv-python) | Apache-2.0 | OCR image processing |
| [trafilatura](https://github.com/adbar/trafilatura) | Apache-2.0 | Web article extraction |
| [FSRS / py-fsrs](https://github.com/open-spaced-repetition/py-fsrs) | MIT | Spaced repetition scheduler |
| [genanki](https://github.com/kerrickstaley/genanki) | MIT | Anki `.apkg` export |
| [winotify](https://github.com/versa-syahptr/winotify) | MIT | Optional Windows toast notifications |

## Data and content sources

| Source | License / terms | Use |
| --- | --- | --- |
| [ECDICT](https://github.com/skywind3000/ECDICT) | MIT | Offline English-Chinese dictionary, phonetics, tags, word forms |
| arXiv API | arXiv terms | Literature discovery |
| OpenAlex | CC0 / OpenAlex terms | Literature discovery |
| Crossref | Crossref terms | Metadata lookup |
| Semantic Scholar API | Semantic Scholar terms | Literature discovery |
| PubMed / NCBI E-utilities | NCBI terms | Literature discovery |
| Unpaywall | Unpaywall terms | Open-access PDF lookup |

## Design and product references

Folio's information architecture was informed by Zotero, Readwise Reader,
PaperLens, Gloss/SciSpace, Koodo Reader and Readest. No source code from those
projects is copied into this repository. The visual system was audited with
[Hallmark](https://github.com/Nutlope/hallmark).

## Notices

- PyMuPDF is dual-licensed by Artifex Software. If you distribute Folio or a
  derivative work, review the AGPL-3.0 obligations or obtain a commercial
  PyMuPDF license.
- Dictionary data is not bundled in the source repository. Release binaries
  include an ECDICT seed database; keep the ECDICT MIT notice with it.
- AI providers, WebDAV servers and literature APIs are configured by the user
  and are governed by their own terms.
