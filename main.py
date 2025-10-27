from fastapi import FastAPI, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pytube import YouTube
import os
import tempfile
import ssl
import uuid

# 🔧 Disable SSL certificate verification for Render
ssl._create_default_https_context = ssl._create_unverified_context

app = FastAPI(title="YouTube Video Downloader API")

# Allow all origins (for React)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "✅ YouTube Downloader API is Live!"}


# 🎥 Fetch video info
@app.post("/api/info")
async def get_video_info(url: str = Form(...)):
    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        if "youtu.be/" in url:
            video_id = url.split("youtu.be/")[-1].split("?")[0]
            url = f"https://www.youtube.com/watch?v={video_id}"

        yt = YouTube(url)

        return {
            "title": yt.title,
            "author": yt.author,
            "views": yt.views,
            "thumbnail_url": yt.thumbnail_url,
            "length": yt.length,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ⬇️ Download endpoint
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

        # Temporary download file
        temp_dir = tempfile.gettempdir()
        filename = f"{uuid.uuid4()}_{yt.title}.{stream.subtype}"
        filepath = os.path.join(temp_dir, filename)

        stream.download(filename=filepath)

        return FileResponse(
            path=filepath,
            filename=f"{yt.title}.{stream.subtype}",
            media_type=f"video/{stream.subtype}"
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
