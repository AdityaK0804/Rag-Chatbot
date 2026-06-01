import yt_dlp

URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

YDL_OPTS = {
    "quiet": True,
    "no_warnings": True,
    "skip_download": True,
    "noplaylist": True,
    "ignoreerrors": True,
}

try:
    with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
        info = ydl.extract_info(URL, download=False)

    if info is None:
        print("FAILED: extract_info returned None (ignoreerrors suppressed the exception)")
    else:
        print("SUCCESS")
        print(f"  title    : {info.get('title')}")
        print(f"  uploader : {info.get('uploader')}")
        print(f"  views    : {info.get('view_count')}")
        print(f"  duration : {info.get('duration')}s")
        print(f"  likes    : {info.get('like_count')}")
        print(f"  comments : {info.get('comment_count')}")

except Exception as e:
    print(f"EXCEPTION: {type(e).__name__}: {e}")