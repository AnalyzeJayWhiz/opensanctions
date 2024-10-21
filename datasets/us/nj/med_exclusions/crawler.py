from pathlib import Path
from typing import Dict
from rigour.mime.types import PDF

import pdfplumber
from normality import collapse_spaces, slugify
from zavod import Context, helpers as h


def parse_pdf_table(
    context: Context, path: Path, save_debug_images=False, headers=None
):
    pdf = pdfplumber.open(path.as_posix())
    settings = {}
    for page_num, page in enumerate(pdf.pages, 1):
        # Find the bottom of the bottom-most rectangle on the page
        bottom = max(page.height - rect["y0"] for rect in page.rects)
        settings["explicit_horizontal_lines"] = [bottom]
        if save_debug_images:
            im = page.to_image()
            im.draw_hline(bottom, stroke=(0, 0, 255), stroke_width=1)
            im.draw_rects(page.find_table(settings).cells)
            im.save(f"page-{page_num}.png")
        assert bottom < (page.height - 5), (bottom, page.height)

        for row in page.extract_table(settings)[1:]:
            if headers is None:
                headers = [slugify(collapse_spaces(cell), sep="_") for cell in row]
                continue
            assert len(headers) == len(row), (headers, row)
            yield dict(zip(headers, row))


def crawl_item(row: Dict[str, str], context: Context):

    address = h.make_address(
        context,
        street=row.pop("street"),
        city=row.pop("city"),
        state=row.pop("state"),
        country_code="US",
        postal_code=row.pop("zip"),
    )

    if not row.get("title"):
        entity = context.make("Company")
        entity.id = context.make_id(row.get("npi_number"), row.get("provider_name"))
        entity.add("name", row.pop("provider_name"))
    else:
        entity = context.make("Person")
        entity.id = context.make_id(row.get("npi_number"), row.get("provider_name"))
        h.apply_name(entity, full=row.pop("provider_name"))
        entity.add("title", row.pop("title"))

    for npi in row.pop("npi_number").split("/"):
        entity.add("npiCode", npi)
    entity.add("country", "us")
    entity.add("address", address)

    sanction = h.make_sanction(context, entity)
    h.apply_date(sanction, "startDate", row.pop("effective_date"))
    sanction.add("provisions", row.pop("action"))

    ended = False

    if row.get("expiration_date") and row.get("expiration_date").upper() not in [
        "PERMANENT",
        "DECEASED",
        "N/A",
    ]:
        h.apply_date(sanction, "endDate", row.pop("expiration_date"))
        end_date = sanction.get("endDate")
        ended = end_date != [] and end_date[0] < context.data_time_iso
    else:
        row.pop("expiration_date")

    if not ended:
        entity.add("topics", "debarment")

    context.emit(entity, target=not ended)
    context.emit(sanction)
    context.emit(address)

    context.audit_data(row)


def crawl(context: Context) -> None:
    path = context.fetch_resource("source.pdf", context.data_url)
    context.export_resource(path, PDF, title=context.SOURCE_TITLE)

    for item in parse_pdf_table(
        context,
        path,
        headers=[
            "provider_name",
            "title",
            "npi_number",
            "street",
            "city",
            "state",
            "zip",
            "action",
            "effective_date",
            "expiration_date",
        ],
    ):
        crawl_item(item, context)
