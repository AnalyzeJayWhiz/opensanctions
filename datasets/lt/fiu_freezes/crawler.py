from typing import List, Optional
from normality import slugify

from zavod import Context
from zavod import helpers as h
from zavod.shed.zyte_api import fetch_html


def unblock_validator(el) -> bool:
    return "Fizinio ar juridinio asmens, kurio turtas įšaldytas" in el.text_content()


def crawl(context: Context):
    doc = fetch_html(context, context.data_url, unblock_validator)
    for p in doc.xpath(".//p"):
        p.tail = p.tail + "\n" if p.tail else "\n"
    table = doc.find('.//div[@class="content-block"]//table')
    assert table is not None, "No table found"

    headers: Optional[List[str]] = None
    for row in table.findall(".//tr"):
        cells = [c.text_content() for c in row.findall(".//td")]
        if headers is None:
            headers = [slugify(k, sep="_") for k in cells]
            continue
        data = dict(zip(headers, cells))
        nr = data.pop("nr")
        company_name = (
            data.pop("fizinio_ar_juridinio_asmens_kurio_turtas_isaldytas_pavadinimas")
            .split("\n")[0]
            .strip()
        )
        reg_nr = data.pop("imones_kodas")
        measures = data.pop("isaldyto_turto_rusis").split("\n")
        legal_grounds = data.pop("reglamentas_kurio_pagrindu_taikomas_turto_isaldymas")
        related_entities = data.pop(
            "fizinis_ar_juridinis_asmuo_kuriam_taikomos_tarptautines_sankcijos"
        ).split("\n")
        company = context.make("Company")
        company.id = context.make_slug(nr, company_name)
        company.add("name", company_name)
        company.add("registrationNumber", reg_nr)
        company.add("topics", "sanction")
        context.emit(company, target=True)

        sanction = h.make_sanction(context, company)
        sanction.add("provisions", measures)
        sanction.add("program", legal_grounds)
        context.emit(sanction)

        for related in related_entities:
            if not len(related.strip()):
                continue
            entity = context.make("LegalEntity")
            entity.id = context.make_slug("sanctioned", related)
            entity.add("name", related)
            context.emit(entity)

            rel = context.make("UnknownLink")
            rel.id = context.make_id(company.id, entity.id)
            rel.add("subject", company)
            rel.add("object", entity)
            context.emit(rel)

        context.audit_data(data)
