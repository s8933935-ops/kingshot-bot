#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Satisfactory RAG - YouTube Knowledge Harvester
Extracts transcripts, chapters, and metadata from Satisfactory guide videos,
and structures them into timestamped RAG chunks.
"""

import os
import sys
import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

# Force UTF-8 on Windows consoles to prevent cp932 emoji errors
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

try:
    import yt_dlp
except ImportError:
    print("Error: yt-dlp is required. Please install with 'pip install yt-dlp'")
    sys.exit(1)

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    YouTubeTranscriptApi = None

RAW_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/raw/youtube"))
PROCESSED_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/processed/youtube_tips.json"))

os.makedirs(RAW_DIR, exist_ok=True)

# Satisfactory v1.0 Launch Date (September 10, 2024)
V1_0_RELEASE_DATE = "20240910"


def extract_video_id(url_or_id: str) -> str:
    """Extract YouTube video ID from various URL formats or raw ID."""
    clean = url_or_id.strip()
    if len(clean) == 11 and re.match(r"^[a-zA-Z0-9_-]{11}$", clean):
        return clean
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"youtu\.be\/([0-9A-Za-z_-]{11})",
        r"youtube\.com\/embed\/([0-9A-Za-z_-]{11})",
        r"youtube\.com\/shorts\/([0-9A-Za-z_-]{11})",
    ]
    for pattern in patterns:
        m = re.search(pattern, clean)
        if m:
            return m.group(1)
    return clean


def get_video_metadata(video_id: str) -> Optional[Dict[str, Any]]:
    """Fetch video metadata and chapters using yt-dlp."""
    ydl_opts = {
        'skip_download': True,
        'extract_flat': False,
        'quiet': True,
        'no_warnings': True,
    }
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return None
            upload_date = info.get('upload_date', '')
            is_v1_0 = upload_date >= V1_0_RELEASE_DATE if upload_date else False

            return {
                "video_id": video_id,
                "title": info.get("title", ""),
                "channel": info.get("uploader", ""),
                "channel_url": info.get("uploader_url", ""),
                "upload_date": upload_date,
                "is_v1_0_verified": is_v1_0,
                "duration_seconds": info.get("duration", 0),
                "view_count": info.get("view_count", 0),
                "url": url,
                "chapters": info.get("chapters") or [],
                "description": info.get("description", "")[:1000]
            }
    except Exception as e:
        print(f"[!] Failed to fetch metadata for {video_id}: {e}")
        return None


def get_transcript(video_id: str) -> List[Dict[str, Any]]:
    """
    Fetch transcript using youtube-transcript-api with fallback to yt-dlp.
    Prioritizes: ja -> en.
    """
    if YouTubeTranscriptApi:
        try:
            ytt = YouTubeTranscriptApi()
            # Try fetching ja then en
            try:
                res = ytt.fetch(video_id, languages=['ja', 'en'])
                return [{"text": s.text, "start": s.start, "duration": s.duration} for s in res]
            except Exception:
                # If specific languages fail, try list() to find available
                tlist = ytt.list(video_id)
                for t in tlist:
                    res = t.fetch()
                    return [{"text": s.text, "start": s.start, "duration": s.duration} for s in res]
        except Exception as e:
            print(f"   [Notice] youtube-transcript-api could not fetch: {e}")

    return []


def chunk_transcript(metadata: Dict[str, Any], transcript: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Split transcript into coherent chunks using chapters or time windows (~120s).
    Attach exact timestamp links.
    """
    video_id = metadata["video_id"]
    chunks = []
    chapters = metadata.get("chapters") or []

    if chapters and len(chapters) > 0:
        # Chapter-based chunking
        for i, chap in enumerate(chapters):
            start_time = chap.get("start_time", 0)
            end_time = chap.get("end_time", metadata["duration_seconds"])
            chap_title = chap.get("title", f"Chapter {i+1}")

            # Collect text in this chapter
            chap_lines = [
                seg["text"].strip()
                for seg in transcript
                if start_time <= seg.get("start", 0) < end_time
            ]
            chap_text = " ".join(chap_lines).strip()
            if not chap_text:
                continue

            timestamp_url = f"https://youtu.be/{video_id}?t={int(start_time)}"
            chunks.append({
                "chunk_id": f"yt_{video_id}_chap_{i+1}",
                "source_type": "youtube_chapter",
                "video_id": video_id,
                "video_title": metadata["title"],
                "channel": metadata["channel"],
                "upload_date": metadata["upload_date"],
                "is_v1_0": metadata["is_v1_0_verified"],
                "chapter_title": chap_title,
                "start_seconds": int(start_time),
                "end_seconds": int(end_time),
                "url": timestamp_url,
                "content": f"【動画解説: {metadata['title']}】\nチャプター: {chap_title}\n時間: {int(start_time)//60}分{int(start_time)%60:02d}秒〜\n内容:\n{chap_text}"
            })
    else:
        # Time-window chunking (approx 120 seconds per chunk)
        WINDOW_SEC = 120
        current_chunk_texts = []
        current_start = 0

        for seg in transcript:
            start = seg.get("start", 0)
            text = seg.get("text", "").strip()
            if not text:
                continue

            if start - current_start > WINDOW_SEC and current_chunk_texts:
                time_url = f"https://youtu.be/{video_id}?t={int(current_start)}"
                merged_text = " ".join(current_chunk_texts).strip()
                chunk_index = len(chunks) + 1
                chunks.append({
                    "chunk_id": f"yt_{video_id}_seg_{chunk_index}",
                    "source_type": "youtube_segment",
                    "video_id": video_id,
                    "video_title": metadata["title"],
                    "channel": metadata["channel"],
                    "upload_date": metadata["upload_date"],
                    "is_v1_0": metadata["is_v1_0_verified"],
                    "chapter_title": f"解説セグメント ({int(current_start)//60}分〜)",
                    "start_seconds": int(current_start),
                    "end_seconds": int(start),
                    "url": time_url,
                    "content": f"【動画解説: {metadata['title']}】\n時間: {int(current_start)//60}分{int(current_start)%60:02d}秒〜\n内容:\n{merged_text}"
                })
                current_chunk_texts = []
                current_start = start

            current_chunk_texts.append(text)

        if current_chunk_texts:
            time_url = f"https://youtu.be/{video_id}?t={int(current_start)}"
            merged_text = " ".join(current_chunk_texts).strip()
            chunk_index = len(chunks) + 1
            chunks.append({
                "chunk_id": f"yt_{video_id}_seg_{chunk_index}",
                "source_type": "youtube_segment",
                "video_id": video_id,
                "video_title": metadata["title"],
                "channel": metadata["channel"],
                "upload_date": metadata["upload_date"],
                "is_v1_0": metadata["is_v1_0_verified"],
                "chapter_title": f"解説セグメント ({int(current_start)//60}分〜)",
                "start_seconds": int(current_start),
                "end_seconds": int(metadata.get("duration_seconds", current_start)),
                "url": time_url,
                "content": f"【動画解説: {metadata['title']}】\n時間: {int(current_start)//60}分{int(current_start)%60:02d}秒〜\n内容:\n{merged_text}"
            })

    return chunks


def harvest_video(video_url_or_id: str) -> Optional[List[Dict[str, Any]]]:
    """Harvest metadata and transcript from a single video, returning RAG chunks."""
    vid = extract_video_id(video_url_or_id)
    print(f"🎬 Harvesting YouTube Video ID: {vid} ...")

    meta = get_video_metadata(vid)
    if not meta:
        print(f"[!] Could not retrieve metadata for {vid}")
        return None

    print(f"   Title: {meta['title']}")
    print(f"   Channel: {meta['channel']} | Upload: {meta['upload_date']} (v1.0: {meta['is_v1_0_verified']})")
    print(f"   Chapters found: {len(meta['chapters'])}")

    transcript = get_transcript(vid)
    print(f"   Transcript segments: {len(transcript)}")

    # Save Raw Data
    raw_path = os.path.join(RAW_DIR, f"{vid}.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump({"metadata": meta, "transcript": transcript}, f, ensure_ascii=False, indent=2)

    chunks = chunk_transcript(meta, transcript)
    print(f"   Generated RAG Chunks: {len(chunks)}")
    return chunks


def search_and_harvest(query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """Search YouTube for Satisfactory guides and harvest them."""
    print(f"🔍 Searching YouTube for query: '{query}' (limit={max_results})...")
    ydl_opts = {
        'skip_download': True,
        'extract_flat': True,
        'quiet': True,
    }
    all_chunks = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            res = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
            entries = res.get('entries', []) or []
            print(f"   Found {len(entries)} candidate videos.")
            for entry in entries:
                vid = entry.get('id')
                if not vid:
                    continue
                chunks = harvest_video(vid)
                if chunks:
                    all_chunks.extend(chunks)
    except Exception as e:
        print(f"[!] YouTube search error: {e}")

    return all_chunks


def save_processed_tips(new_chunks: List[Dict[str, Any]]):
    """Save or append chunks to processed youtube_tips.json."""
    existing = []
    if os.path.exists(PROCESSED_FILE):
        try:
            with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = []

    # Merge by chunk_id
    chunk_map = {c["chunk_id"]: c for c in existing}
    for c in new_chunks:
        chunk_map[c["chunk_id"]] = c

    merged = list(chunk_map.values())
    with open(PROCESSED_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Saved {len(merged)} total YouTube Tips chunks to: {PROCESSED_FILE}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python youtube_harvester.py <video_url_or_id>")
        print("  python youtube_harvester.py --search \"Satisfactory 1.0 パイプ\" [limit]")
        sys.exit(0)

    if sys.argv[1] == "--search":
        search_query = sys.argv[2]
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 3
        results = search_and_harvest(search_query, max_results=limit)
        if results:
            save_processed_tips(results)
    else:
        video_arg = sys.argv[1]
        results = harvest_video(video_arg)
        if results:
            save_processed_tips(results)
