"""Explicitly synthetic adapters for offline integration. Never live city data."""
from copy import deepcopy
from datetime import datetime, timezone
from importlib.resources import files
import json
import math

from astana_contracts import validate_payload

SYNTHETIC_WARNING = "SYNTHETIC: integration fixtures only; not real city recommendations."


def now():
    return datetime.now(timezone.utc).isoformat()


def distance(a, b):
    lat1, lat2 = math.radians(a["lat"]), math.radians(b["lat"])
    dlat, dlon = lat2 - lat1, math.radians(b["lon"] - a["lon"])
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371000 * 2 * math.asin(min(1, math.sqrt(h)))


class FixtureRepository:
    def __init__(self):
        cases = json.loads(files("astana_contracts").joinpath("data/contracts.examples.json").read_text())["cases"]
        seed = next(c["instance"] for c in cases if c["name"] == "place_valid")
        self.places = []
        for index, (name, lat, lon, indoor) in enumerate([
            ("SYNTHETIC — indoor fixture", 51.090, 71.420, True),
            ("SYNTHETIC — outdoor fixture", 51.091, 71.418, False),
            ("SYNTHETIC — second indoor fixture", 51.088, 71.422, True),
        ]):
            place = deepcopy(seed)
            place["id"] = "synthetic:place:" + ["one", "two", "three"][index]
            place["name"], place["location"] = name, {"lat": lat, "lon": lon}
            place["facts"][0]["value"] = indoor
            self.places.append(validate_payload("Place", place))

    async def get(self, place_id):
        return deepcopy(next((p for p in self.places if p["id"] == place_id), None))

    async def list_places(self, *, bbox=None, query=None, categories=None, cursor=None, limit=50):
        if cursor is not None and (not cursor.isascii() or not cursor.isdecimal() or len(cursor) > 8):
            raise ValueError("Invalid cursor")
        offset = int(cursor or "0")
        result = sorted(self.places, key=lambda p: p["id"])
        if bbox:
            w, s, e, n = bbox
            result = [p for p in result if w <= p["location"]["lon"] <= e and s <= p["location"]["lat"] <= n]
        if query:
            result = [p for p in result if query.casefold() in (p["name"] + " " + p["description"]).casefold()]
        if categories:
            result = [p for p in result if set(categories) & set(p["categories"])]
        end = offset + limit
        return {"places": deepcopy(result[offset:end]), "next_cursor": str(end) if end < len(result) else None}

    async def nearby(self, *, origin, radius_meters, limit=100):
        candidates = [p for p in self.places if distance(origin, p["location"]) <= radius_meters]
        return deepcopy(sorted(candidates, key=lambda p: (distance(origin, p["location"]), p["id"]))[:limit])

    async def data_status(self):
        return {"sources": [], "total_places": len(self.places), "checked_at": now()}


class FixtureRetriever:
    def __init__(self, repository):
        self.repository = repository

    async def retrieve(self, request):
        validate_payload("RetrievalRequest", request)
        places = await self.repository.nearby(origin=request["origin"], radius_meters=request["radius_meters"], limit=request["candidate_limit"])
        return validate_payload("RetrievalResponse", {
            "places": places,
            "hits": [{"place_id": p["id"], "score": float(len(places) - i), "score_kind": "deterministic", "matched_fact_keys": []} for i, p in enumerate(places)],
            "strategy": "synthetic_distance_fixture", "warnings": [SYNTHETIC_WARNING, "Fixture retrieval ignores semantic query intent."],
        })


class FixtureContext:
    async def enrich_places(self, *, places, request):
        return {"places": deepcopy(places), "warnings": [SYNTHETIC_WARNING], "degraded_services": []}

    async def estimate_route(self, *, origin, destinations, transport, return_to_origin, start_at):
        if transport != "walking":
            raise ValueError("Unsupported transport")
        points = [origin, *destinations, *([origin] if return_to_origin else [])]
        meters = sum(distance(a, b) for a, b in zip(points, points[1:])) * 1.35
        return validate_payload("RouteEstimate", {
            "method": "approximate", "provider": "synthetic_fixture", "transport": transport,
            "distance_meters": round(meters, 1), "duration_seconds": math.ceil(meters / 1.2),
            "includes_return": return_to_origin, "geometry": None,
            "assumptions": [SYNTHETIC_WARNING, "Straight-line distance × 1.35; assumed walking speed 1.2 m/s. Barriers and street access are unverified."],
            "evidence": [{"id": "synthetic:evidence:route-formula", "source_name": "Synthetic integration route formula", "source_type": "synthetic", "source_url": "https://example.invalid/astana-compass/fixtures/route-formula", "source_record_id": "synthetic:route-formula:v1", "retrieved_at": now(), "is_synthetic": True}], "generated_at": now(),
        })
