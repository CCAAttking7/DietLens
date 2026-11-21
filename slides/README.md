# DietLens Assignment 2 slide package

This folder contains the classroom presentation for the System Analysis and Design Assignment 2 progress presentation.

## Files

- `DietLens-Assignment-2-System-Design.pptx` — seven-slide, 16:9 presentation for a six-minute talk.
- `DietLens-Assignment-2-Speaker-Notes.md` — timing and Chinese delivery notes.
- `generate_deck.py` — reproducible source for the PPTX; diagrams are vector shapes, so they remain editable in PowerPoint.
- `diagrams/` — editable Mermaid source for the logical, deployment and interaction views used in the deck.

## Regenerate

The repository does not need a runtime dependency for the application. To regenerate the deck locally, use a Python environment with `python-pptx`:

```bash
python -m venv /tmp/dietlens-pptx
source /tmp/dietlens-pptx/bin/activate
pip install python-pptx Pillow lxml
python slides/generate_deck.py
```

The source reads the actual product screenshot at `artifacts/dietlens-round-3/after/dietlens-home-1440.png`. If that evidence file is unavailable, the deck still generates with the evidence frame left empty; the slide should then be regenerated after the artifact is restored.

## Evidence basis

The architecture and decisions are derived from the existing repository, including `DietLens_SRS.pdf`, `docs/product-logic.md`, `docs/model-routing.md`, `docs/profile-workflow.md`, `api_server.py`, `dietlens_mvp/harness.py`, `dietlens_mvp/tools.py` and `dietlens_mvp/models.py`. The deck intentionally presents the current product boundary rather than claiming a complete nutrition-tracking engine.
