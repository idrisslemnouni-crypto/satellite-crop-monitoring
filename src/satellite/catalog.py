"""Small, fixed STAC manifests; never require private credentials or full tiles."""

import json
import urllib.request

ENDPOINT = "https://earth-search.aws.element84.com/v1"


def discover(config: dict) -> list[dict]:
    query = {
        "collections": [config["collection"]],
        "bbox": config["bbox"],
        "datetime": f"{config['year']}-04-01T00:00:00Z/{config['year']}-10-31T23:59:59Z",
        "limit": 100,
        "query": {"eo:cloud_cover": {"lt": 35}},
    }
    request = urllib.request.Request(
        ENDPOINT + "/search",
        data=json.dumps(query).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        collection = json.load(response)
    items = collection["features"]
    matched = collection.get("numberMatched", collection.get("context", {}).get("matched"))
    if matched is not None and matched > len(items):
        raise ValueError("Query truncated: narrow the scope before selecting scenes")
    selected = []
    for month in config["months"]:
        subset = [
            i
            for i in items
            if i["properties"]["datetime"].startswith(f"{config['year']}-{month:02d}")
        ]
        if not subset:
            raise ValueError(f"No candidate scene for month {month}")
        selected.append(min(subset, key=lambda i: (i["properties"]["eo:cloud_cover"], i["id"])))
    return selected
