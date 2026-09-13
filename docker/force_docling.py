from pathlib import Path


pipeline_path = Path("/app/libs/ktem/ktem/index/file/pipelines.py")
ui_path = Path("/app/libs/ktem/ktem/index/file/ui.py")
ingest_path = Path("/app/libs/kotaemon/kotaemon/indices/ingests/files.py")
docling_loader_path = Path("/app/libs/kotaemon/kotaemon/loaders/docling_loader.py")
pdf_viewer_path = Path("/app/libs/ktem/ktem/assets/js/pdf_viewer.js")
app_path = Path("/app/libs/ktem/ktem/app.py")
simple_reasoning_path = Path("/app/libs/ktem/ktem/reasoning/simple.py")
chat_page_path = Path("/app/libs/ktem/ktem/pages/chat/__init__.py")
chat_panel_path = Path("/app/libs/ktem/ktem/pages/chat/chat_panel.py")
citation_qa_path = Path(
    "/app/libs/kotaemon/kotaemon/indices/qa/citation_qa.py"
)
citation_utils_path = Path(
    "/app/libs/kotaemon/kotaemon/indices/qa/utils.py"
)

pipeline_source = pipeline_path.read_text()
old_param = 'reader_mode: str = Param("default", help="The reader mode")'
new_param = 'reader_mode: str = Param("docling", help="The reader mode")'
if pipeline_source.count(old_param) != 1:
    raise RuntimeError("Unexpected Kotaemon reader_mode declaration")
pipeline_source = pipeline_source.replace(old_param, new_param)

old_setting = '''"reader_mode": {
                "name": "File loader",
                "value": "default",'''
new_setting = '''"reader_mode": {
                "name": "File loader",
                "value": "docling",'''
if pipeline_source.count(old_setting) != 1:
    raise RuntimeError("Unexpected Kotaemon file-loader setting")
pipeline_path.write_text(pipeline_source.replace(old_setting, new_setting))

pipeline_source = pipeline_path.read_text()
old_retrieval_count = '''"num_retrieval": {
                "name": "Number of document chunks to retrieve",
                "value": 10,'''
new_retrieval_count = '''"num_retrieval": {
                "name": "Number of document chunks to retrieve",
                "value": 40,'''
old_retrieval_mode = '''"retrieval_mode": {
                "name": "Retrieval mode",
                "value": "hybrid",'''
new_retrieval_mode = '''"retrieval_mode": {
                "name": "Retrieval mode",
                "value": "vector",'''
if pipeline_source.count(old_retrieval_count) != 1:
    raise RuntimeError("Unexpected Kotaemon retrieval count setting")
if pipeline_source.count(old_retrieval_mode) != 1:
    raise RuntimeError("Unexpected Kotaemon retrieval mode setting")
pipeline_path.write_text(
    pipeline_source.replace(old_retrieval_count, new_retrieval_count).replace(
        old_retrieval_mode, new_retrieval_mode
    )
)

ui_source = ui_path.read_text()
old_override = 'settings[f"index.options.{self._index.id}.reader_mode"] = "default"'
if ui_source.count(old_override) != 2:
    raise RuntimeError("Unexpected Kotaemon quick-upload overrides")
ui_path.write_text(ui_source.replace(old_override, old_override.replace('"default"', '"docling"')))

# The upstream image always constructs an Azure-only vision endpoint, even when
# no Azure endpoint or key is configured. That makes Docling try and fail to
# caption every detected figure and leaves huge base64 image chunks in the
# embedding index. Keep figure captioning off for this OpenAI/local demo; the
# original PDF and page metadata remain available for citations.
ingest_source = ingest_path.read_text()
old_vlm_assignment = '''adobe_reader.vlm_endpoint = (
    azure_reader.vlm_endpoint
) = docling_reader.vlm_endpoint = getattr(flowsettings, "KH_VLM_ENDPOINT", "")'''
new_vlm_assignment = '''adobe_reader.vlm_endpoint = azure_reader.vlm_endpoint = getattr(
    flowsettings, "KH_VLM_ENDPOINT", ""
)
docling_reader.vlm_endpoint = ""'''
if ingest_source.count(old_vlm_assignment) != 1:
    raise RuntimeError("Unexpected Kotaemon VLM endpoint assignment")
ingest_path.write_text(ingest_source.replace(old_vlm_assignment, new_vlm_assignment))

# These Toyota manuals are born-digital PDFs: every one of the 517 files has an
# embedded text layer. Disable raster OCR while retaining Docling's layout and
# table analysis. This avoids running EasyOCR over 5,677 already-searchable pages.
docling_source = docling_loader_path.read_text()
old_converter = '''        try:
            from docling.document_converter import DocumentConverter
        except ImportError:
            raise ImportError("Please install docling: 'pip install docling'")

        return DocumentConverter()'''
new_converter = '''        try:
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            from docling.document_converter import DocumentConverter, PdfFormatOption
        except ImportError:
            raise ImportError("Please install docling: 'pip install docling'")

        pdf_options = PdfPipelineOptions()
        pdf_options.do_ocr = False
        return DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options)
            }
        )'''
if docling_source.count(old_converter) != 1:
    raise RuntimeError("Unexpected Kotaemon Docling converter declaration")
docling_loader_path.write_text(docling_source.replace(old_converter, new_converter))

# Kotaemon 0.0.1 imports pdfjs-viewer-element from Skypack at runtime. That CDN
# build currently fails, leaving citation previews blank. Use the already
# bundled PDF.js viewer directly in a same-origin iframe instead.
viewer_source = pdf_viewer_path.read_text()
old_viewer_element = '''                <pdfjs-viewer-element id="pdf-viewer" viewer-path="GR_FILE_ROOT_PATH/file=PDFJS_PREBUILT_DIR" locale="en" phrase="true">
                </pdfjs-viewer-element>'''
new_viewer_element = '''                <iframe id="pdf-viewer"
                  data-viewer-root="GR_FILE_ROOT_PATH/file=PDFJS_PREBUILT_DIR/web/viewer.html"
                  title="Cited PDF page"
                  style="width: 100%; height: 100%; border: 0;">
                </iframe>'''
if viewer_source.count(old_viewer_element) != 1:
    raise RuntimeError("Unexpected Kotaemon PDF viewer element")
viewer_source = viewer_source.replace(old_viewer_element, new_viewer_element)
viewer_source = viewer_source.replace(
    'var iframe = document.querySelector("#pdf-viewer").iframe;',
    'var iframe = document.querySelector("#pdf-viewer");',
)
old_open = '''    current_src = pdfViewer.getAttribute("src");
    if (current_src != src) {
      pdfViewer.setAttribute("src", src);
    }
    // pdfViewer.setAttribute("phrase", phrase);
    // pdfViewer.setAttribute("search", search);
    pdfViewer.setAttribute("page", page);'''
new_open = '''    var viewerRoot = pdfViewer.getAttribute("data-viewer-root");
    var viewerSrc = viewerRoot + "?file=" + encodeURIComponent(src) + "#page=" + page;
    if (pdfViewer.getAttribute("src") != viewerSrc) {
      pdfViewer.setAttribute("src", viewerSrc);
    }'''
if viewer_source.count(old_open) != 1:
    raise RuntimeError("Unexpected Kotaemon PDF open handler")
pdf_viewer_path.write_text(viewer_source.replace(old_open, new_open))

app_source = app_path.read_text()
old_cdn = '''            "<script type='module' "
            "src='https://cdn.skypack.dev/pdfjs-viewer-element'>"
            "</script>"'''
if app_source.count(old_cdn) != 1:
    raise RuntimeError("Unexpected Kotaemon external PDF viewer import")
app_source = app_source.replace(old_cdn, "")
old_index_startup = '''        self.index_manager = IndexManager(self)
        self.index_manager.on_application_startup()

        for index in self.index_manager.indices:'''
new_index_startup = '''        self.index_manager = IndexManager(self)
        self.index_manager.on_application_startup()
        # Legacy graph indices can persist in Kotaemon's database even after the
        # feature flags are disabled. This demo uses only the normal file index.
        self.index_manager._indices = [
            index for index in self.index_manager.indices
            if index.__class__.__name__ == "FileIndex"
        ]

        for index in self.index_manager.indices:'''
if app_source.count(old_index_startup) != 1:
    raise RuntimeError("Unexpected Kotaemon index startup")
app_path.write_text(app_source.replace(old_index_startup, new_index_startup))

# Keep demo answers deliberately short while retaining evidence-only behavior
# and essential safety warnings.
reasoning_source = simple_reasoning_path.read_text()
old_system_prompt = '"value": ("This is a question answering system."),'
new_system_prompt = '''"value": (
                    "You are AI Mechanic Assistant. Answer only from the provided "
                    "service-manual evidence. Use the fewest words that answer "
                    "correctly. Prefer one sentence or 2-4 short bullets. Give the "
                    "exact value or action first. Keep essential safety warnings. "
                    "For removal, installation, replacement, diagnosis, or repair "
                    "questions, first identify any build-date or equipment variants, "
                    "then preserve the manual's numbered order and include prerequisite "
                    "removals; never jump straight to the final action. For a long "
                    "procedure, do not imitate the manual's step numbers with an "
                    "incomplete list. Instead give concise ordered phases, explicitly "
                    "label them as a summary, name the major trim, restraint, electrical, "
                    "and safety prerequisites, cite the full applicable page range, and "
                    "direct the user to those pages for every substep. If the vehicle's "
                    "build date or equipment is not supplied, show every applicable "
                    "variant and its page range before the summary. "
                    "If evidence is insufficient, say: Not found in the selected "
                    "manuals. Preserve source citations."
                ),'''
if reasoning_source.count(old_system_prompt) != 1:
    raise RuntimeError("Unexpected Kotaemon system prompt default")
simple_reasoning_path.write_text(
    reasoning_source.replace(old_system_prompt, new_system_prompt)
)

# Keep the evidence panel focused on cited material only. The retrieval pipeline
# can use 40 chunks internally, but the user should never see that working set.
reasoning_source = simple_reasoning_path.read_text()
old_evidence_output = '''            yield from with_citation
            if without_citation:
                yield from without_citation'''
new_evidence_output = '''            # Show at most three cited pages. Do not expose every retrieved chunk.
            yield from with_citation[:3]'''
if reasoning_source.count(old_evidence_output) != 1:
    raise RuntimeError("Unexpected Kotaemon evidence output")
simple_reasoning_path.write_text(
    reasoning_source.replace(old_evidence_output, new_evidence_output)
)

# Automatically replace the raw evidence list with the highest-ranked cited PDF
# page in the right panel. Kotaemon's PDF.js integration also highlights the
# cited phrase on the rendered page when it can match the text layer.
chat_source = chat_page_path.read_text()
old_pdfview_start = '''function() {
    setTimeout(fullTextSearch(), 100);

    // Get all links and attach click event'''
new_pdfview_start = '''function() {
    setTimeout(fullTextSearch(), 100);

    setTimeout(() => {
        const evidenceRoot = document.querySelector("#html-info-panel > div:last-child");
        if (!evidenceRoot) return;
        const firstCitedPage = Array.from(
            evidenceRoot.querySelectorAll("details.evidence")
        ).find((item) => item.querySelector("mark") && item.querySelector("a.pdf-link"));
        if (firstCitedPage) firstCitedPage.querySelector("a.pdf-link").click();
    }, 250);

    // Get all links and attach click event'''
if chat_source.count(old_pdfview_start) != 1:
    raise RuntimeError("Unexpected Kotaemon PDF completion hook")
chat_page_path.write_text(chat_source.replace(old_pdfview_start, new_pdfview_start))

chat_source = chat_page_path.read_text()
old_quick_upload = "with gr.Accordion(label=quick_upload_label) as _:"
new_quick_upload = "with gr.Accordion(label=quick_upload_label, visible=False) as _:"
if chat_source.count(old_quick_upload) != 1:
    raise RuntimeError("Unexpected Kotaemon quick-upload accordion")
chat_source = chat_source.replace(old_quick_upload, new_quick_upload)
chat_source = chat_source.replace('label="Chat settings",', 'label="Answer options",')
chat_page_path.write_text(chat_source)

# Remove Kotaemon/GraphRAG wording from the empty-state copy and chat input.
panel_source = chat_panel_path.read_text()
old_placeholder = '''PLACEHOLDER_TEXT = (
        "This is the beginning of a new conversation.\\n"
        "Start by uploading a file or a web URL. "
        "Visit Files tab for more options (e.g: GraphRAG)."
    )'''
new_placeholder = '''PLACEHOLDER_TEXT = (
        "Ask a question about the indexed service manuals. "
        "Answers include concise, page-linked evidence."
    )'''
if panel_source.count(old_placeholder) != 1:
    raise RuntimeError("Unexpected Kotaemon empty-state copy")
panel_source = panel_source.replace(old_placeholder, new_placeholder)
panel_source = panel_source.replace(
    '"Type a message, use @WebSearch, or tag a file with @filename"',
    '"Ask a question about the vehicle"',
)
chat_panel_path.write_text(panel_source)

qa_source = citation_qa_path.read_text()
qa_source = qa_source.replace(
    "answer the question at the end in detail with clear explanation.",
    "answer the question using the fewest words that remain correct.",
)
qa_source = qa_source.replace(
    "then provide answer with clear explanation.",
    "then answer using the fewest words that remain correct.",
)
citation_qa_path.write_text(qa_source)

# Kotaemon's stock citation matcher accepts a 35% fuzzy subsequence. Generic
# workshop language ("Torque", "bolt A", units) can therefore map a correct
# answer to an unrelated manual page. Citation phrases are copied from context,
# so require an exact textual match while tolerating PDF line-wrap whitespace.
utils_source = citation_utils_path.read_text()
old_find_text = '''def find_text(search_span, context, min_length=5):
    search_span, context = search_span.lower(), context.lower()

    sentence_list = search_span.split("\\n")
    context = context.replace("\\n", " ")

    matches_span = []
    # don't search for small text
    if len(search_span) > min_length:
        for sentence in sentence_list:
            match_results = SequenceMatcher(
                None,
                sentence,
                context,
                autojunk=False,
            ).get_matching_blocks()

            matched_blocks = []
            for _, start, length in match_results:
                if length > max(len(sentence) * 0.25, min_length):
                    matched_blocks.append((start, start + length))

            if matched_blocks:
                start_index = min(start for start, _ in matched_blocks)
                end_index = max(end for _, end in matched_blocks)
                length = end_index - start_index

                if length > max(len(sentence) * 0.35, min_length):
                    matches_span.append((start_index, end_index))

    if matches_span:
        # merge all matches into one span
        final_span = min(start for start, _ in matches_span), max(
            end for _, end in matches_span
        )
        matches_span = [final_span]

    return matches_span'''
new_find_text = '''def find_text(search_span, context, min_length=12):
    import re

    search_span = search_span.strip()
    if len(search_span) <= min_length:
        return []

    # Preserve original offsets for highlighting, but allow line wrapping and
    # repeated spaces introduced by PDF extraction.
    tokens = re.split(r"\\s+", search_span)
    pattern = r"\\s+".join(re.escape(token) for token in tokens if token)
    match = re.search(pattern, context, flags=re.IGNORECASE)
    return [(match.start(), match.end())] if match else []'''
if utils_source.count(old_find_text) != 1:
    raise RuntimeError("Unexpected Kotaemon fuzzy citation matcher")
citation_utils_path.write_text(utils_source.replace(old_find_text, new_find_text))

qa_source = citation_qa_path.read_text()
old_all_doc_matches = '''        for quote in evidences:
            matched_excerpts = []
            for doc in docs:
                matches = find_text(quote, doc.text)

                for start, end in matches:
                    if "|" not in doc.text[start:end]:
                        spans[doc.doc_id].append(
                            {
                                "start": start,
                                "end": end,
                            }
                        )
                        matched_excerpts.append(doc.text[start:end])

            # print("Matched citation:", quote, matched_excerpts),'''
new_single_doc_match = '''        for quote in evidences:
            # Retrieved docs are relevance ordered. Bind each quotation to the
            # first exact match only, instead of highlighting every similar page.
            for doc in docs:
                matches = find_text(quote, doc.text)
                if not matches:
                    continue
                start, end = matches[0]
                if "|" not in doc.text[start:end]:
                    spans[doc.doc_id].append({"start": start, "end": end})
                    break'''
if qa_source.count(old_all_doc_matches) != 1:
    raise RuntimeError("Unexpected Kotaemon citation document matcher")
citation_qa_path.write_text(
    qa_source.replace(old_all_doc_matches, new_single_doc_match)
)
