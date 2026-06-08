import os
import json
from dataclasses import dataclass
from typing import List, Dict, Optional, Any

@dataclass
class ContextSlice:
    docs: List[Any]
    total_tokens: int
    citations_manifest: Dict[str, str]


@dataclass
class EvidenceDoc:
    """Lightweight envelope for pillar grounding data.

    Mirrors the contract expected by ai_question_generator.py:
    - content: rendered text block ready for the prompt
    - source: provenance string (e.g., "Verizon DBIR 2025")
    - relevance_score: 1.0 for direct sector hit, lower for anchors-only
    """
    content: str            # the rendered likelihood block (ready for the prompt)
    source: str             # e.g. "Verizon DBIR 2025" — flows into metadata
    relevance_score: float  # 1.0 for a direct sector hit, lower for anchors-only


class CorpusRetriever:
    def __init__(self, bucket_name: Optional[str] = None):
        self.bucket_name = bucket_name or os.environ.get('CORPUS_BUCKET_NAME')
        self.index_path = 'corpus/_index.json'

    @property
    def enabled(self) -> bool:
        """Return True if pillar reader has DBIR data loaded.

        Retied from the old bucket/index check to the pillar reader.
        When OIC_PILLARS_ENABLED=0, reader loads nothing -> has_series False.
        """
        try:
            from corpus.pillar_reader import get_pillar_reader
            from corpus.pillar_crosswalk import SERIES_VERIZON_DBIR
            return get_pillar_reader().has_series(SERIES_VERIZON_DBIR)
        except Exception:
            return False

    def retrieve_risk_identification_context(
        self,
        industry: str,
        region: str,
        organization_size: Optional[str] = None,
        max_results: int = 5,
        tier: str = "free"
    ) -> List[EvidenceDoc]:
        """Retrieve likelihood grounding for the given industry.

        Returns a list of EvidenceDoc (currently 0 or 1 docs). Even when
        coverage is False, returns a doc with corpus-wide anchors — they are
        useful sector-agnostic framing. The block honestly says "anchors only".

        region & organization_size accepted but unused — likelihood is industry-only.
        """
        # region & organization_size reserved for future extensions
        del region, organization_size, max_results, tier  # unused in likelihood-only mode

        if not self.enabled:
            return []

        from corpus.pillar_reader import get_pillar_reader

        slice_ = get_pillar_reader().slice_likelihood(industry)
        block = self._render_likelihood_block(slice_)
        score = 1.0 if slice_.get("coverage") else 0.5
        source = slice_.get("source") or "Verizon DBIR"

        return [EvidenceDoc(content=block, source=source, relevance_score=score)]

    def _render_likelihood_block(self, slice_: Dict) -> str:
        """Render the compact LIKELIHOOD block from slice data.

        Honest rendering: coverage False renders "No sector-specific DBIR row"
        plus corpus-wide anchors. Never derives a probability.
        """
        industry = slice_.get("industry_canonical", "Unknown")
        source = slice_.get("source") or "Verizon DBIR"
        provenance = slice_.get("provenance", {})
        edition = provenance.get("edition", "")
        coverage = slice_.get("coverage", False)
        sector = slice_.get("sector") or {}
        overall = slice_.get("overall") or {}

        lines = []
        lines.append("=" * 70)
        lines.append(f"INDUSTRY LIKELIHOOD GROUNDING — {industry}")
        if edition:
            lines.append(f"Source: {source} (incident corpus; counts, not base rates)")
        else:
            lines.append(f"Source: {source} (incident corpus; counts, not base rates)")
        lines.append("=" * 70)

        if coverage and sector:
            # Sector-specific composition
            if sector.get("top_patterns"):
                lines.append(f"Top attack patterns: {sector['top_patterns']}")
            if sector.get("threat_actors"):
                lines.append(f"Threat actors: {sector['threat_actors']}")
            if sector.get("actor_motives"):
                lines.append(f"Actor motives: {sector['actor_motives']}")
            if sector.get("notable"):
                lines.append(f"Notable: {sector['notable']}")
            if sector.get("incidents") and sector.get("breaches"):
                lines.append(f"Counts: {sector['incidents']} incidents, {sector['breaches']} breaches")
        else:
            lines.append(f"No sector-specific DBIR row for {industry}; corpus-wide anchors only.")

        # Corpus anchors (always present when DBIR loaded)
        if overall:
            anchors = []
            if overall.get("ransomware_share_of_breaches") is not None:
                anchors.append(f"ransomware share of breaches {overall['ransomware_share_of_breaches']}")
            if overall.get("smb_ransomware_share") is not None:
                anchors.append(f"SMB ransomware share {overall['smb_ransomware_share']}")
            if overall.get("median_ransom_paid_usd") is not None:
                anchors.append(f"median ransom paid ${overall['median_ransom_paid_usd']:,}")
            if overall.get("top_breach_patterns"):
                top = overall["top_breach_patterns"]
                if isinstance(top, dict):
                    # Take first entry
                    first = list(top.items())[0] if top else None
                    if first:
                        anchors.append(f"top breach pattern: {first[0]} ({first[1]})")
            if anchors:
                lines.append(f"Corpus anchors: {'; '.join(anchors)}")

        lines.append("=" * 70)
        lines.append("Use this to frame WHICH threats are credible for this sector. These are")
        lines.append("corpus composition figures, not annual probabilities — do NOT state a")
        lines.append(f'derived percent chance of breach. Cite "{source}", never the YAML.')
        lines.append("=" * 70)

        return "\n".join(lines)

    def retrieve_coaching_context(
        self,
        user_question: str,
        industry: str,
        region: str,
        fair_component: Optional[str] = None,
        max_results: int = 5
    ) -> List:
        return []

    def format_context_for_prompt(self, contexts: List[EvidenceDoc], max_length: Optional[int] = None) -> str:
        """Join EvidenceDoc content blocks for the prompt.

        Args:
            contexts: List of EvidenceDoc objects
            max_length: Optional truncation limit (preserved for API compatibility)

        Returns:
            Concatenated content string
        """
        if not contexts:
            return ""

        joined = "\n\n".join(doc.content for doc in contexts)

        # Honor max_length if provided (simple truncation with warning)
        if max_length and len(joined) > max_length:
            joined = joined[:max_length]
            joined += f"\n[...truncated to {max_length} chars...]"

        return joined

def get_rag_engine(enable_fallback: bool = True) -> CorpusRetriever:
    """Factory function maintaining the same signature for backwards compatibility."""
    return CorpusRetriever()
