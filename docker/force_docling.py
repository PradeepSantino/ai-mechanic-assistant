from pathlib import Path


pipeline_path = Path("/app/libs/ktem/ktem/index/file/pipelines.py")
ui_path = Path("/app/libs/ktem/ktem/index/file/ui.py")
ingest_path = Path("/app/libs/kotaemon/kotaemon/indices/ingests/files.py")
docling_loader_path = Path("/app/libs/kotaemon/kotaemon/loaders/docling_loader.py")
pdf_viewer_path = Path("/app/libs/ktem/ktem/assets/js/pdf_viewer.js")
app_path = Path("/app/libs/ktem/ktem/app.py")

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
app_path.write_text(app_source.replace(old_cdn, ""))
