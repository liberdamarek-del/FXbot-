"""Evidence items and factor clusters (modules 3, 36, 39, 50).

Every material statement of the analysis is an Evidence item with its
taxonomy class (module 3), the factor cluster it belongs to (module 36),
its direction for the pair, its data quality and the data it rests on.

Confluence is counted per CLUSTER, never per item: higher yields, a
stronger rate differential and a policy hike are one RATES cluster, not
three signals.
"""

from dataclasses import dataclass

# independent evidence clusters
PRICE_TREND = "PRICE_TREND"          # D1/H4 trend, momentum (technical direction)
RATES_REPRICING = "RATES_REPRICING"  # change of the expected rate path (module 21)
CARRY = "CARRY"                      # rate differential level, vol-adjusted (module 24)
POSITIONING = "POSITIONING"          # CFTC positioning (module 25)
RISK = "RISK"                        # global risk regime x measured pair beta (module 31)
COMMODITY = "COMMODITY"              # commodity link measured from data (module 30)
EVENT = "EVENT"                      # scheduled event risk (module 47) - gate, not direction
INTERVENTION = "INTERVENTION"        # module 33 - context / counterforce only
DATA = "DATA"                        # data quality notes

DIRECTIONAL_CLUSTERS = (PRICE_TREND, RATES_REPRICING, CARRY, POSITIONING, RISK, COMMODITY)
FUNDAMENTAL_CLUSTERS = (RATES_REPRICING, CARRY, POSITIONING, RISK, COMMODITY)

TAXONOMY = ("OBSERVATION", "DERIVED METRIC", "INTERPRETATION", "HYPOTHESIS", "DECISION")


@dataclass(frozen=True)
class Evidence:
    cluster: str
    direction: str            # BUY / SELL / NONE (for the pair)
    weight: int               # 1 supporting, 2 strong; 0 = context only
    text: str                 # Czech explanation for the user
    taxonomy: str = "DERIVED METRIC"
    source: str = ""
    as_of: str = ""
    quality: str = "A"
    role: str = "DIRECTION"   # DIRECTION / COUNTERFORCE / GATE / CONTEXT

    def to_dict(self) -> dict:
        return {
            "cluster": self.cluster,
            "direction": self.direction,
            "weight": self.weight,
            "text": self.text,
            "taxonomy": self.taxonomy,
            "source": self.source,
            "as_of": self.as_of,
            "quality": self.quality,
            "role": self.role,
        }


def cluster_votes(items: list[Evidence], clusters=DIRECTIONAL_CLUSTERS) -> dict[str, str]:
    """One vote per cluster: the direction with the larger total weight
    inside the cluster (ties = NONE). Counterforce items do not vote."""
    votes = {}

    for cluster in clusters:
        buy = sum(e.weight for e in items if e.cluster == cluster and e.role == "DIRECTION" and e.direction == "BUY")
        sell = sum(e.weight for e in items if e.cluster == cluster and e.role == "DIRECTION" and e.direction == "SELL")

        if buy > sell:
            votes[cluster] = "BUY"
        elif sell > buy:
            votes[cluster] = "SELL"
        elif buy or sell:
            votes[cluster] = "CONFLICT"

    return votes


def opposite(direction: str) -> str:
    return {"BUY": "SELL", "SELL": "BUY"}.get(direction, "NONE")
