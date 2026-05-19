# Multi-Agent Enterprise Contract Generator

Python app that turns a natural language request into a professional NDA PDF using Gemini, LangGraph, LangChain tools, Streamlit, HTML/CSS templates, and WeasyPrint.

## Run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
streamlit run app.py
```

Set `GOOGLE_API_KEY` in `.env`.

Optional:

```text
GEMINI_MODEL=gemini-2.5-flash
```

## Architecture

```text
Streamlit UI
  -> LangGraph StateGraph
  -> Supervisor -> Planner -> Legal Writer -> Compliance -> Formatter -> PDF Tool -> END
  -> tools/registry.py -> load_template, save_document, generate_pdf
```

## Concepts Demonstrated

**LLM fundamentals:** Gemini Flash receives role-based prompts for planning, drafting, and compliance review. The default is `gemini-2.5-flash`; override it with `GEMINI_MODEL`.

**Tool calling:** LangChain `@tool` functions expose template loading, document storage, and PDF generation. Agents invoke tools through `.invoke(...)`.

**MCP-style architecture:** Tools live outside agents and are exposed through `tools/registry.py`, making them modular, discoverable, and independently consumable.

**Multi-agent orchestration:** LangGraph coordinates a shared state across specialized agents, each improving the contract artifact before PDF export.

## Project Structure

```text
enterprise-doc-gen/
+-- agents/
+-- tools/
+-- graph/
+-- templates/
+-- output/
+-- app.py
+-- requirements.txt
+-- .env.example
```

## Notes

WeasyPrint requires native GTK/Pango libraries on Windows. If you see a missing
`libgobject-2.0-0` error:

```bash
# Install MSYS2, then in the MSYS2 UCRT64 terminal:
pacman -S mingw-w64-ucrt-x86_64-gtk3 mingw-w64-ucrt-x86_64-pango mingw-w64-ucrt-x86_64-gdk-pixbuf2
```

Add `C:\msys64\ucrt64\bin` to your Windows PATH, restart the terminal, and run
Streamlit again. The app writes generated HTML and PDF files into `output/`.
