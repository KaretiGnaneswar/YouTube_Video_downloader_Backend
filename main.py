from fastapi import FastAPI, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pytube import YouTube
import os
import tempfile
import uuid
import ssl

# Fix SSL certificate issue
ssl._create_default_https_context = ssl._create_unverified_context

app = FastAPI(title="YouTube Video Downloader API")

# Allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change "*" to your React URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "🎥 YouTube Downloader API is running!"}


# 🔹 Fetch video info
@app.post("/api/info")
async def get_video_info(url: str = Form(...)):
    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        # Convert short links
        if "youtu.be/" in url:
            video_id = url.split("youtu.be/")[-1].split("?")[0]
            url = f"https://www.youtube.com/watch?v={video_id}"

        yt = YouTube(url)
        video_streams = yt.streams.filter(progressive=True, file_extension="mp4").order_by("resolution").desc()
        audio_streams = yt.streams.filter(only_audio=True).order_by("abr").desc()

        mins, secs = divmod(yt.length, 60)
        hrs, mins = divmod(mins, 60)
        length = f"{hrs:02d}:{mins:02d}:{secs:02d}" if hrs > 0 else f"{mins:02d}:{secs:02d}"

        return {
            "title": yt.title,
            "author": yt.author,
            "views": yt.views,
            "thumbnail_url": yt.thumbnail_url,
            "length": length,
            "available_streams": {
                "video": [{"itag": s.itag, "resolution": s.resolution, "fps": s.fps} for s in video_streams],
                "audio": [{"itag": s.itag, "bitrate": s.abr} for s in audio_streams],
            },
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# 🔹 Download video/audio
@app.post("/api/download")
async def download_video(url: str = Form(...), quality: str = Form("highest")):
    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        if "youtu.be/" in url:
            video_id = url.split("youtu.be/")[-1].split("?")[0]
            url = f"https://www.youtube.com/watch?v={video_id}"

        yt = YouTube(url)

        if quality == "highest":
            stream = yt.streams.get_highest_resolution()
        elif quality == "audio_only":
            stream = yt.streams.get_audio_only()
        else:
            stream = yt.streams.filter(res=quality, progressive=True).first() or yt.streams.get_highest_resolution()

        if not stream:
            raise HTTPException(status_code=400, detail="No suitable stream found")

        # Temp file
        safe_title = "".join(c for c in yt.title if c.isalnum() or c in (" ", ".", "_")).rstrip()
        filename = f"{uuid.uuid4()}_{safe_title}.{stream.subtype}"
        filepath = os.path.join(tempfile.gettempdir(), filename)

        stream.download(filename=filepath)

        return FileResponse(
            path=filepath,
            filename=f"{safe_title}.{stream.subtype}",
            media_type=f"video/{stream.subtype}",
            headers={"Content-Disposition": f"attachment; filename={safe_title}.{stream.subtype}"}
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
