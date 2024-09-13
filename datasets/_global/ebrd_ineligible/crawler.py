from lxml import html
from normality import slugify, collapse_spaces
from rigour.mime.types import CSV
from rigour.mime.types import HTML
import csv

from zavod import Context
from zavod import helpers as h


def crawl_mutual_enforcement(context: Context):
    path = context.fetch_resource(
        "source.csv",
        "https://www.ebrd.com/sites/Satellite?c=Page&cid=1395305341160&pagename=EBRD%2FPage%2FSolrSearchAndFilterAsCSV",
        data={
            "subtype": "ineligibleentity",
            "safsortbychecked": "Title_sort",
            "safsortorderchecked": "ascending",
        },
        method="POST",
    )
    context.export_resource(path, CSV, title=context.SOURCE_TITLE)
    with open(path, "r") as fh:
        reader = csv.reader(fh)
        headers = None

        # Find the first non-empty line, assumed to be the header
        for row in reader:
            if row:  # Check for a non-empty row
                headers = [col.strip() for col in row]  # Clean up any extra spaces
                break
        dict_reader = csv.DictReader(fh, fieldnames=headers)

        collected_rows = list(dict_reader)
        for row in collected_rows:
            name = row.pop("Firm Name")
            address = row.pop("Address")
            country = row.pop("Nationality")
            entity = context.make("LegalEntity")
            entity.id = context.make_id(name, address, country)
            entity.add("name", name)
            entity.add("address", address)
            entity.add("country", country)

            sanction = h.make_sanction(context, entity)
            sanction.add("reason", row.pop("Prohibited Practice"))
            sanction.add("publisher", row.pop("Originating Institution"))
            h.apply_date(sanction, "startDate", row.pop("Ineligible From"))
            h.apply_date(sanction, "endDate", row.pop("Ineligible Until"))
            h.apply_date(sanction, "date", row.pop("Notice Effective At EBRD"))

            entity.add("topics", "debarment")
            context.emit(entity, target=True)
            context.emit(sanction)
            context.audit_data(row)


def crawl_ebrd_initiated(context: Context):
    path = context.fetch_resource("source.html", context.data_url)
    context.export_resource(path, HTML, title=context.SOURCE_TITLE)
    with open(path, "r") as fh:
        doc = html.parse(fh)
    # Check for 'EBRD-initiated sanctions' section
    section = doc.xpath("//h2[.//text()[contains(., 'EBRD-initiated sanctions')]]")
    if not section:
        context.log.warning("Section for 'EBRD-initiated sanctions' not found")
        return

    # Find the first table after the section
    table = section[0].xpath(".//following::table[1]")
    if not table:
        context.log.warning("Table for 'EBRD-initiated sanctions' not found")
        return

    table = table[0]

    headers = None
    for row in table.findall(".//tr"):
        if headers is None:
            headers = [slugify(c.text_content(), "_") for c in row.findall("./td")]
            headers = headers[:-2] + ["from", "to"] + headers[-1:]
            continue
        cells = [collapse_spaces(c.text_content()) for c in row.findall("./td")]
        cells = dict(zip(headers, cells))
        if "prohibited_practice" not in cells:
            continue

        name = cells.pop("firm_name")
        nationality = cells.pop("nationality")
        entity = context.make("Company")
        entity.id = context.make_id(name, nationality)
        entity.add("name", name)
        entity.add("topics", "debarment")
        entity.add("country", nationality)

        sanction = h.make_sanction(context, entity)
        sanction.add("reason", cells.pop("prohibited_practice"))
        h.apply_date(sanction, "startDate", cells.pop("from"))
        h.apply_date(sanction, "endDate", cells.pop("to"))

        full = cells.pop("address")
        address = h.make_address(context, full=full, country=nationality)
        h.apply_address(context, entity, address)

        context.emit(entity, target=True)
        context.emit(sanction)


def crawl_third_party(context: Context):
    path = context.fetch_resource("source.html", context.data_url)
    context.export_resource(path, HTML, title=context.SOURCE_TITLE)

    with open(path, "r") as fh:
        doc = html.parse(fh)

    # Find the section and corresponding table for 'Sanctions resulting from third party findings'
    section = doc.xpath(
        "//h2[.//strong[text()='Sanctions resulting from third party findings']]"
    )
    if not section:
        context.log.warning(
            "Section for 'Sanctions resulting from third party findings' not found"
        )
        return

    table = section[0].xpath(".//following::table[1]")
    if not table:
        context.log.warning(
            "Table for 'Sanctions resulting from third party findings' not found"
        )
        return

    table = table[0]

    for row_idx, row in enumerate(table.findall(".//tr")):
        cells = [collapse_spaces(c.text_content()) for c in row.findall("./td")]

        if row_idx == 0:
            # Skip the first row with "Firm name", "Address", etc.
            continue
        elif row_idx == 1:
            # Skip the second row with "From" and "To" headers
            continue
        else:
            # Map cells based on the table structure
            data = {
                "firm_name": cells[0],
                "address": cells[1],
                "nationality": cells[2],
                "ineligible_from": cells[3],
                "ineligible_to": cells[4],
                "enforcement_decision": cells[5],
                "jurisdiction": cells[6],
                "prohibited_practice": cells[7],
            }

            name = data.pop("firm_name")
            address = data.pop("address")
            nationality = data.pop("nationality")

            entity = context.make("LegalEntity")
            entity.id = context.make_id(name, address, nationality)
            entity.add("name", name)
            entity.add("address", address)
            entity.add("country", nationality)
            entity.add("topics", "debarment")

            sanction = h.make_sanction(context, entity)
            sanction.add("reason", data.pop("prohibited_practice"))
            sanction.add("authority", data.pop("jurisdiction"))
            h.apply_date(sanction, "startDate", data.pop("ineligible_from"))
            h.apply_date(sanction, "endDate", data.pop("ineligible_to"))
            h.apply_date(
                sanction,
                "listingDate",
                data.pop("enforcement_decision"),
            )

            context.emit(entity, target=True)
            context.emit(sanction)


def crawl(context: Context):
    crawl_ebrd_initiated(context)
    crawl_third_party(context)
    crawl_mutual_enforcement(context)
