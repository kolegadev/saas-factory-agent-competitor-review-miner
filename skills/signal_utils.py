"""Shared utilities for signal creation and keyword extraction."""
import re, uuid, random
from datetime import datetime, timezone
from collections import defaultdict

PAIN_KEYWORDS = {
    "emotional": ["frustrated", "hate doing", "ridiculous", "nightmare", "drowning in", "sick of", "tired of", "fed up", "annoying", "infuriating", "exhausting", "overwhelming", "stressful", "pain in the", "headache", "drag", "chore", "ordeal"],
    "time_waste": ["wasting time", "takes forever", "takes hours", "all day", "whole morning", "every single day", "constantly", "repeatedly", "over and over", "spend half my day", "time sink", "black hole"],
    "manual_process": ["manual", "by hand", "one by one", "copy paste", "copy-paste", "copying and pasting", "re-enter", "retype", "double entry", "duplicate data", "workaround", "hack together", "piece together", "stitch together", "band-aid", "duct tape"],
    "tool_gaps": ["spreadsheet", "excel", "google sheets", "no good tool", "no software", "nothing does this", "if only there was", "why doesn't anyone make", "surprised nobody has", "missing tool", "gap in the market", "unsolved problem"],
    "workarounds": ["workaround", "temporary fix", "make do", "get by", "cobble together", "jerry-rig", "improvise", "kludge", "bodge", "not ideal but", "better than nothing", "only way I know"],
    "willingness_to_pay": ["would pay", "I'd pay", "happy to pay", "take my money", "shut up and", "worth paying for", "would subscribe", "would buy", "need this yesterday", "instant purchase", "sign me up", "where do I pay"]
}


def extract_keywords(text, keyword_dict):
    text_lower = text.lower()
    matched = defaultdict(list)
    for category, words in keyword_dict.items():
        for w in words:
            if w in text_lower:
                matched[category].append(w)
    return dict(matched)


def create_signal(raw_text, platform, source_url, engagement_score=0, reply_count=0, simulated=False):
    sig_id = f"sig-{uuid.uuid4().hex[:12]}"
    keywords = extract_keywords(raw_text, PAIN_KEYWORDS)
    return {
        "signal_id": sig_id,
        "raw_text": raw_text,
        "platform": f"simulated_{platform}" if simulated else platform,
        "source_url": source_url,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "recency_hours": random.randint(1, 72),
        "author_hint": None,
        "engagement": {"upvotes": engagement_score, "replies": reply_count, "shares": 0},
        "pain_keywords_matched": keywords.get("emotional", []) + keywords.get("time_waste", []) + keywords.get("manual_process", []),
        "wtp_keywords_matched": keywords.get("willingness_to_pay", []),
        "context": raw_text,
        "language": "en",
        "geo_hint": None,
        "simulated": simulated
    }
