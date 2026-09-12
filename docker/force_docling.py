from pathlib import Path


pipeline_path = Path("/app/libs/ktem/ktem/index/file/pipelines.py")
ui_path = Path("/app/libs/ktem/ktem/index/file/ui.py")
ingest_path = Path("/app/libs/kotaemon/kotaemon/indices/ingests/files.py")
docling_loader_path = Path("/app/libs/kotaemon/kotaemon/loaders/docling_loader.py")

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
