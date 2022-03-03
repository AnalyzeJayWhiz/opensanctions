# https://www.mediawiki.org/wiki/Wikibase/API
# https://www.wikidata.org/w/api.php?action=help&modules=wbgetentities
import json
import structlog
from functools import cache
from datetime import timedelta
from typing import Any, Dict, Optional

from opensanctions import settings
from opensanctions.core import Context
from opensanctions.core.db import engine_read
from opensanctions.core.cache import all_cached, Cache, randomize_cache
from opensanctions.wikidata.lang import pick_obj_lang
from opensanctions.util import normalize_url

WD_API = "https://www.wikidata.org/w/api.php"
log = structlog.getLogger(__name__)


def wikibase_getentities(context: Context, ids, cache_days=None, **kwargs):
    params = {**kwargs, "format": "json", "ids": ids, "action": "wbgetentities"}
    return context.fetch_json(WD_API, params=params, cache_days=cache_days)


def get_entity(context: Context, qid: str) -> Optional[Dict[str, Any]]:
    data = wikibase_getentities(
        context,
        qid,
        cache_days=14,
    )
    return data.get("entities", {}).get(qid)


@cache
def get_label(context: Context, qid: str) -> Optional[str]:
    data = wikibase_getentities(
        context,
        qid,
        cache_days=100,
        props="labels",
    )
    entity = data.get("entities", {}).get(qid)
    label = pick_obj_lang(entity.get("labels", {}))
    return label
