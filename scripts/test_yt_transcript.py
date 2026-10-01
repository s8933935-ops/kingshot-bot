import sys
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp

video_id = "U5Wy69v553c"
print(f"Testing transcript for {video_id}...")
try:
    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
    print("Available transcripts:")
    for t in transcript_list:
        print(f"  - lang={t.language_code}, is_generated={t.is_generated}")
    trans = transcript_list.find_transcript(['ja', 'en']).fetch()
    print(f"Fetched segments: {len(trans)}")
    print("Sample segment:", trans[0] if trans else "Empty")
except Exception as e:
    print(f"youtube_transcript_api error: {e}")

print("\nTesting yt-dlp subtitles...")
ydl_opts = {
    'skip_download': True,
    'writesubtitles': True,
    'writeautomaticsub': True,
    'subtitleslangs': ['ja', 'en'],
    'quiet': True
}
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
    subs = info.get('subtitles') or {}
    auto_subs = info.get('automatic_captions') or {}
    print(f"Manual subs: {list(subs.keys())}")
    print(f"Auto subs: {list(auto_subs.keys())[:5]}")
