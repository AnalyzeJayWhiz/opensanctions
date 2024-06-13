# Imiona i nazwisk
# Pseudonim
# Data urodzenia
# Miejsce urodzenia
# Rodzaj i nr dokumentu stwierdzającego tożsamość
# Inne informacje
# Uzasadnienie wpisu na listę
# Data umieszczenia na liście
#
# Names and surnames
# Pseudonym
# Date of birth
# Place of birth
# Type and number of the identity document
# Other informations
# Justification for entry on the list
# Date of listing

from normality import collapse_spaces
from rigour.mime.types import CSV
from typing import Dict
import csv

from zavod import Context
from zavod import helpers as h
from zavod.shed.un_sc import get_legal_entities, get_persons

FORMATS = ["%d.%m.%Y"]
PDF_URL = "https://www.gov.pl/attachment/2fc03b3b-a5f6-4d08-80d1-728cdb71d2d6"
POLAND_PROGRAM = "art. 118 ustawy z dnia 1 marca 2018 r. o przeciwdziałaniu praniu pieniędzy i finansowaniu terroryzmu"
UN_SC_CONSOLIDATED_URL = "https://scsanctions.un.org/resources/xml/en/consolidated.xml"
UN_SC_PREFIXES = ["TA", "QD"]
UN_SC_PREFIX = "unsc"


def parse_date(string):
    return h.parse_date(string.replace(" r.", ""), FORMATS)


def crawl_row(context: Context, row: Dict[str, str]):
    entity = context.make("Person")
    name = row.pop("Imiona i nazwisk")
    birthplace = row.pop("Miejsce urodzenia")
    entity.id = context.make_id(birthplace, name)
    entity.add("name", name)
    entity.add("alias", row.pop("Pseudonim").split("\n"))
    birth_country = birthplace.split(",")[-1]
    entity.add("birthPlace", birthplace, lang="pol")
    entity.add("birthCountry", birth_country, lang="pol")
    entity.add("birthDate", parse_date(row.pop("Data urodzenia")))
    entity.add("address", row.pop("location full") or None)
    entity.add("country", row.pop("location country") or None)

    entity.add("nationality", row.pop("narodowość"))
    entity.add("topics", "sanction")

    sanction = h.make_sanction(context, entity)
    sanction.add("listingDate", parse_date(row.pop("Data umieszczenia na liście")))
    sanction.add(
        "reason", collapse_spaces(row.pop("Uzasadnienie wpisu na listę")), lang="pol"
    )
    sanction.add("program", POLAND_PROGRAM, "pol")

    context.emit(entity, target=True)
    context.emit(sanction)

    context.audit_data(row)


def check_updates(context: Context):
    doc = context.fetch_html(context.dataset.url)
    doc.make_links_absolute(context.dataset.url)
    materials = doc.findall(".//a[@class='file-download']")
    if len(materials) != 1:
        context.log.warning(
            f"Expected 1 materials downloads but found {len(materials)}"
        )
    else:
        url = materials[0].get("href")
        if url != PDF_URL:
            context.log.warning(
                "Materials download URL has changed. Time to update manually.", url=url
            )
        else:
            res = context.http.head(url)
            last_modified = res.headers.get("last-modified")
            if last_modified != "Wed, 27 Sep 2023 10:56:50 GMT":
                context.log.warning(
                    "Materials download file has been updated. Time to update manually.",
                    last_modified=last_modified,
                )


def crawl(context: Context):
    check_updates(context)

    path = context.fetch_resource("source.csv", context.data_url)
    context.export_resource(path, CSV, title=context.SOURCE_TITLE)
    with open(path, "r") as fh:
        for row in csv.DictReader(fh):
            crawl_row(context, row)

    path = context.fetch_resource("source.xml", UN_SC_CONSOLIDATED_URL)
    context.export_resource(
        path, "text/xml", title="UN Security Council Consolidated list"
    )
    doc = context.parse_resource_xml(path)

    for _node, entity in get_persons(context, UN_SC_PREFIX, doc, UN_SC_PREFIXES):
        context.emit(entity, target=True)

    for _node, entity in get_legal_entities(context, UN_SC_PREFIX, doc, UN_SC_PREFIXES):
        context.emit(entity, target=True)
