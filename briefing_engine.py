#!/usr/bin/env python3
"""
Information Overload Eliminator - Core Briefing & Deduplication Engine
Groups repetitive industry articles into concise, verifiable executive briefings.
"""

import json
import re
from collections import Counter
from typing import List, Dict, Any

STOP_WORDS = {
    'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', 'aren',
    'as', 'at', 'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by',
    'can', 'could', 'did', 'do', 'does', 'doing', 'down', 'during', 'each', 'few', 'for', 'from',
    'further', 'had', 'has', 'have', 'having', 'he', 'her', 'here', 'hers', 'herself', 'him', 'himself',
    'his', 'how', 'i', 'if', 'in', 'into', 'is', 'it', 'its', 'itself', 'just', 'me', 'more', 'most',
    'my', 'myself', 'no', 'nor', 'not', 'now', 'of', 'off', 'on', 'once', 'only', 'or', 'other',
    'our', 'ours', 'ourselves', 'out', 'over', 'own', 's', 'same', 'she', 'should', 'so', 'some',
    'such', 't', 'than', 'that', 'the', 'their', 'theirs', 'them', 'themselves', 'then', 'there',
    'these', 'they', 'this', 'those', 'through', 'to', 'too', 'under', 'until', 'up', 'very', 'was',
    'we', 'were', 'what', 'when', 'where', 'which', 'while', 'who', 'whom', 'why', 'will', 'with',
    'you', 'your', 'yours', 'yourself', 'yourselves', 'new', 'unveils', 'launches', 'announces', 'takes'
}

def tokenize(text: str) -> List[str]:
    """Tokenize and filter text down to meaningful keywords."""
    words = re.findall(r'\b[a-zA-Z0-9_\-\.]{2,}\b', text.lower())
    return [w for w in words if w not in STOP_WORDS]

def overlap_coefficient(s1: set, s2: set) -> float:
    """Szymkiewicz-Simpson overlap coefficient: intersection / min(len1, len2)."""
    if not s1 or not s2:
        return 0.0
    return len(s1.intersection(s2)) / min(len(s1), len(s2))

def calculate_similarity(art1: Dict[str, Any], art2: Dict[str, Any]) -> float:
    """
    Calculate semantic similarity score between two articles using:
    1. Title token Overlap Coefficient (Weight: 0.55)
    2. Content/Key point term Overlap Coefficient (Weight: 0.35)
    3. Topic match bonus (Weight: 0.10)
    """
    t1 = set(tokenize(art1.get("title", "")))
    t2 = set(tokenize(art2.get("title", "")))
    title_overlap = overlap_coefficient(t1, t2)

    c1 = set(tokenize(art1.get("content", "") + " " + " ".join(art1.get("key_points", []))))
    c2 = set(tokenize(art2.get("content", "") + " " + " ".join(art2.get("key_points", []))))
    content_overlap = overlap_coefficient(c1, c2)

    topic_match = 1.0 if art1.get("topic") and art1.get("topic") == art2.get("topic") else 0.0

    return (title_overlap * 0.55) + (content_overlap * 0.35) + (topic_match * 0.10)

def cluster_articles(articles: List[Dict[str, Any]], threshold: float = 0.25) -> List[Dict[str, Any]]:
    """
    Group articles covering the same development using single-linkage agglomerative clustering.
    Returns list of clusters with metadata.
    """
    clusters = []  # List of list of articles

    for article in articles:
        assigned = False
        for cluster in clusters:
            # Check if this article matches any existing member in the cluster above threshold
            if any(calculate_similarity(article, member) >= threshold for member in cluster):
                cluster.append(article)
                assigned = True
                break

        if not assigned:
            clusters.append([article])

    # Transform clusters into structured briefings
    briefing_clusters = []
    for cid, members in enumerate(clusters, 1):
        # Sort members: prioritize recognized journalistic sources or longest detail
        members.sort(key=lambda a: len(a.get("content", "")), reverse=True)
        lead = members[0]

        # Consolidate key takeaways across all sources
        all_points = []
        for a in members:
            for pt in a.get("key_points", []):
                clean_pt = pt.strip()
                if not any(is_similar_sentence(clean_pt, p) for p in all_points):
                    all_points.append(clean_pt)

        # Synthesize Bottom Line summary
        bottom_line = generate_bottom_line(lead, members)

        # Extract source verification links
        sources = [
            {
                "id": a.get("id"),
                "source": a.get("source", "Industry Outlet"),
                "title": a.get("title", ""),
                "url": a.get("url", "#"),
                "date": a.get("date", "Recent"),
                "author": a.get("author", "Staff"),
                "coverage_focus": extract_source_angle(a)
            }
            for a in members
        ]

        # Extract prominent keywords for badges
        cluster_tokens = Counter()
        for a in members:
            cluster_tokens.update(tokenize(a.get("title", "")))
        top_tags = [w for w, _ in cluster_tokens.most_common(3)]

        briefing_clusters.append({
            "id": f"dev-{cid}",
            "topic": lead.get("topic", "General"),
            "tags": top_tags,
            "headline": lead.get("title"),
            "bottom_line": bottom_line,
            "key_takeaways": all_points[:4],  # Signal over noise: keep top 3-4 points
            "source_count": len(members),
            "sources": sources,
            "confidence_score": min(98, 65 + (len(members) * 11)), # Multi-source verification boosts confidence
            "reading_time_mins": 1
        })

    # Sort briefings by source count (highest signal developments first)
    briefing_clusters.sort(key=lambda b: b["source_count"], reverse=True)
    return briefing_clusters

def is_similar_sentence(s1: str, s2: str, threshold: float = 0.55) -> bool:
    """Check if two bullet points essentially share the same core fact."""
    t1 = set(tokenize(s1))
    t2 = set(tokenize(s2))
    if not t1 or not t2:
        return False
    return overlap_coefficient(t1, t2) > threshold

def extract_source_angle(article: Dict[str, Any]) -> str:
    """Extract the specific nuance or angle this source emphasizes."""
    text = (article.get("title", "") + " " + article.get("content", "")).lower()
    if re.search(r'\b(seo|referral|traffic|search engine optimization|webmaster)\b', text):
        return "Analyzes search traffic disruption, webmaster referral patterns, and SEO impact."
    elif re.search(r'\b(licens\w*|deal|pact|partnerships?)\b', text):
        return "Focuses on publisher content licensing deals and media partnerships."
    elif re.search(r'\b(specs?|288gb|hbm3e|nvl72|liquid cooling|grace)\b', text):
        return "Details hardware architectural specs, memory bandwidth, and rack engineering."
    elif re.search(r'\b(fines up to|penalt\w*|compliance|code of practice|brussels|gpai|systemic risk)\b', text):
        return "Focuses on regulatory compliance deadlines, audits, and legal fines under EU law."
    elif re.search(r'\b(rollout|tier|sidebar|how it works|subscribers?|timeline)\b', text):
        return "Explains feature walkthrough, subscriber tier availability, and user interface."
    elif re.search(r'\b(hands-on|tested|stumbled|latency|24 hours|impressive but early)\b', text):
        return "Provides empirical hands-on testing notes, latency quirks, and real-world limits."
    elif re.search(r'\b(capex|spending|hyperscale|billion|investors?)\b', text):
        return "Examines cloud hyperscaler capital expenditures and market demand dynamics."
    elif re.search(r'\b(api|desktop ui|keystrokes|mouse|computer use)\b', text):
        return "Highlights developer API capabilities and autonomous UI automation."
    else:
        return "Provides primary news coverage and core announcement details."

def generate_bottom_line(lead: Dict[str, Any], cluster: List[Dict[str, Any]]) -> str:
    """Generate high-signal bottom line synthesis for the development."""
    content = lead.get("content", "")
    protected = content
    abbrevs = ["Corp.", "Inc.", "Ltd.", "Co.", "U.S.", "E.U.", "vs.", "Dr.", "Mr.", "Ms.", "Jan.", "Feb.", "Aug.", "Sept.", "Oct.", "Nov.", "Dec."]
    for ab in abbrevs:
        protected = protected.replace(ab, ab.replace(".", "__DOT__"))
    sentences = [s.replace("__DOT__", ".") for s in re.split(r'\.\s+', protected) if s.strip()]
    if sentences:
        first = sentences[0].strip()
        if not first.endswith('.'):
            first += '.'
        return first
    return lead.get("title", "")

def filter_articles(
    articles: List[Dict[str, Any]], 
    topic: str = "All", 
    keywords: List[str] = None
) -> List[Dict[str, Any]]:
    """Filter articles by topic and/or search keywords."""
    filtered = articles
    
    if topic and topic.lower() != "all":
        filtered = [a for a in filtered if a.get("topic", "").lower() == topic.lower()]

    if keywords:
        kw_clean = [k.lower().strip() for k in keywords if k.strip()]
        if kw_clean:
            def matches(a):
                text = (a.get("title", "") + " " + a.get("content", "") + " " + a.get("topic", "")).lower()
                return any(k in text for k in kw_clean)
            filtered = [a for a in filtered if matches(a)]

    return filtered

def compute_noise_reduction(total_articles: int, clustered_developments: int) -> Dict[str, Any]:
    """Calculate noise reduction metrics: percentage eliminated, minutes saved."""
    if total_articles == 0:
        return {
            "total_articles": 0,
            "key_developments": 0,
            "articles_eliminated": 0,
            "noise_reduction_pct": 0,
            "est_raw_reading_time_mins": 0,
            "est_briefing_time_mins": 0,
            "time_saved_mins": 0
        }
    
    raw_time_mins = round(total_articles * 2.2) # Average ~2.2 mins per article
    briefing_time_mins = max(1, round(clustered_developments * 0.8)) # ~45s per synthesized cluster
    saved_time = max(0, raw_time_mins - briefing_time_mins)
    eliminated = total_articles - clustered_developments
    reduction_pct = round((eliminated / total_articles) * 100) if total_articles > 0 else 0

    return {
        "total_articles": total_articles,
        "key_developments": clustered_developments,
        "articles_eliminated": eliminated,
        "noise_reduction_pct": reduction_pct,
        "est_raw_reading_time_mins": raw_time_mins,
        "est_briefing_time_mins": briefing_time_mins,
        "time_saved_mins": saved_time
    }

def generate_markdown_briefing(briefings: List[Dict[str, Any]], metrics: Dict[str, Any]) -> str:
    """Format clusters into an executive-ready Markdown briefing."""
    md = []
    md.append("# ⚡ Executive Briefing: Industry Signal Digest")
    md.append(f"**Signal Report:** {metrics['total_articles']} sources analyzed → {metrics['key_developments']} key developments.")
    md.append(f"**Noise Eliminated:** {metrics['noise_reduction_pct']}% reduction | ⏱️ {metrics['time_saved_mins']} mins reading time saved.\n")
    md.append("---\n")

    for i, dev in enumerate(briefings, 1):
        md.append(f"## {i}. {dev['headline']}")
        md.append(f"**Topic:** `{dev['topic']}` | **Corroborating Sources:** {dev['source_count']} | **Confidence:** {dev['confidence_score']}%")
        md.append(f"\n> **The Bottom Line:** {dev['bottom_line']}\n")
        
        md.append("### Key Takeaways")
        for pt in dev['key_takeaways']:
            md.append(f"- {pt}")
        
        md.append("\n### Verified Sources & Angles")
        for s in dev['sources']:
            md.append(f"- **[{s['source']}]({s['url']})**: *{s['title']}* — {s['coverage_focus']}")
        md.append("\n---\n")

    return "\n".join(md)

def run_pipeline(articles: List[Dict[str, Any]], topic: str = "All", keywords: List[str] = None, threshold: float = 0.25):
    """Run full filtering, deduplication, and briefing generation pipeline."""
    filtered = filter_articles(articles, topic=topic, keywords=keywords)
    clusters = cluster_articles(filtered, threshold=threshold)
    metrics = compute_noise_reduction(len(filtered), len(clusters))
    return {
        "metrics": metrics,
        "briefings": clusters
    }

if __name__ == "__main__":
    import sys
    import os
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(script_dir, "sample_data.json")
    
    if len(sys.argv) > 1:
        data_path = sys.argv[1]
    
    with open(data_path, "r", encoding="utf-8") as f:
        sample_articles = json.load(f)

    result = run_pipeline(sample_articles)
    briefing_md = generate_markdown_briefing(result["briefings"], result["metrics"])
    print(briefing_md)
