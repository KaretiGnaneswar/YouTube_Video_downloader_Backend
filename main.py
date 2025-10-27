from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pytube import YouTube
from pydantic import BaseModel
import os
import tempfile
import uuid

app = FastAPI(title="YouTube Video Downloader API")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/")
async def root():
    return {"message": "🎥 YouTube Downloader API is running! Visit /docs for details."}


# ------------------------------
# 🔹 Fetch Video Info
# ------------------------------
class InfoRequest(BaseModel):
    url: str

@app.post("/api/info")
async def get_video_info(req: InfoRequest):
    try:
        url = req.url.strip()

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        # Convert short links
        if "youtu.be/" in url:
            video_id = url.split("youtu.be/")[-1].split("?")[0]
            url = f"https://www.youtube.com/watch?v={video_id}"

        yt = YouTube(url)

        # Get available streams
        video_streams = yt.streams.filter(progressive=True, file_extension="mp4").order_by("resolution").desc()
        audio_streams = yt.streams.filter(only_audio=True).order_by("abr").desc()

        # Duration format
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


# ------------------------------
# 🔹 Download Video or Audio
# ------------------------------
class DownloadRequest(BaseModel):
    url: str
    quality: str = "highest"

@app.post("/api/download")
async def download_video(req: DownloadRequest):
    try:
        url = req.url.strip()
        quality = req.quality

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        if "youtu.be/" in url:
            video_id = url.split("youtu.be/")[-1].split("?")[0]
            url = f"https://www.youtube.com/watch?v={video_id}"

        yt = YouTube(url)

        # Choose appropriate stream
        if quality == "highest":
            stream = yt.streams.get_highest_resolution()
        elif quality == "audio_only":
            stream = yt.streams.get_audio_only()
        else:
            stream = yt.streams.filter(res=quality, progressive=True).first() or yt.streams.get_highest_resolution()

        if not stream:
            raise HTTPException(status_code=400, detail="No suitable stream found")

        # Temporary file setup
        safe_title = "".join(c for c in yt.title if c.isalnum() or c in (" ", ".", "_")).rstrip()
        filename = f"{uuid.uuid4()}_{safe_title}.{stream.subtype}"
        filepath = os.path.join(tempfile.gettempdir(), filename)

        # Download
        stream.download(filename=filepath)

        return FileResponse(
            path=filepath,
            filename=f"{safe_title}.{stream.subtype}",
            media_type=f"video/{stream.subtype}",
            headers={"Content-Disposition": f"attachment; filename={safe_title}.{stream.subtype}"}
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ------------------------------
# Run the server
# ------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
