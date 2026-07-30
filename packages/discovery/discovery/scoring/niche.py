"""Niche relevance scoring for universal discovery."""

import re
from typing import Any


def niche_relevance(profile: dict[str, Any], profile_data: dict[str, Any]) -> float:
    """Score how relevant a profile is to the campaign niche (0.0 – 1.0).

    Combines:
      - keyword overlap between profile bio/text and niche_keywords
      - hashtag overlap between profile's hashtags and target hashtags
    """
    bio = (profile.get("biography") or profile.get("bio") or "").lower()
    username = (profile.get("username") or profile.get("handle") or "").lower()
    full_name = (profile.get("full_name") or profile.get("fullName") or "").lower()
    categories = " ".join(profile.get("categories") or []).lower()
    search_text = f"{bio} {username} {full_name} {categories}"

    profile_hashtags_raw = profile.get("hashtags", [])
    profile_hashtags = [h.lower().lstrip("#") for h in profile_hashtags_raw]

    niche_keywords = [str(k).lower() for k in profile_data.get("niche_keywords", [])]
    target_hashtags = [str(h).lower().lstrip("#") for h in profile_data.get("hashtags", [])]

    niche_score = _keyword_overlap(search_text, niche_keywords)
    hashtag_score = _hashtag_overlap(profile_hashtags, target_hashtags)

    return 0.6 * niche_score + 0.4 * hashtag_score


def _keyword_overlap(text: str, keywords: list[str]) -> float:
    if not keywords:
        return 0.5
    matches = sum(1 for kw in keywords if kw and len(kw) > 2 and _safe_keyword_match(text, kw))
    return min(matches / max(len(keywords) * 0.3, 1), 1.0)


def _hashtag_overlap(profile_tags: list[str], target_tags: list[str]) -> float:
    if not target_tags:
        return 0.5
    profile_set = set(profile_tags)
    target_set = set(target_tags)
    if not profile_set:
        return 0.3
    overlap = len(profile_set & target_set)
    return min(overlap / max(len(target_set) * 0.25, 1), 1.0)


def _safe_keyword_match(text: str, keyword: str) -> bool:
    try:
        pattern = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
        return bool(pattern.search(text))
    except re.error:
        return keyword in text
