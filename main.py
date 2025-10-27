from fastapi import FastAPI, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pytube import YouTube
import os
import tempfile
import uuid
import ssl
import certifi

# Disable SSL verification and force system certificates
ssl._create_default_https_context = ssl._create_unverified_context

app = FastAPI(title="YouTube Downloader API")

# Allow frontend requests (React)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this to your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "✅ YouTube Downloader Backend is Live on Render!"}


@app.post("/api/info")
async def get_video_info(url: str = Form(...)):
    try:
        # Fix invalid URLs
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        if "youtu.be/" in url:
            video_id = url.split("youtu.be/")[-1].split("?")[0]
            url = f"https://www.youtube.com/watch?v={video_id}"

        yt = YouTube(url)

        mins, secs = divmod(yt.length, 60)
        length = f"{mins}m {secs}s"

        return {
            "title": yt.title,
            "author": yt.author,
            "views": yt.views,
            "thumbnail_url": yt.thumbnail_url,
            "length": length,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch info: {e}")


@app.post("/api/download")
async def download_video(url: str = Form(...), quality: str = Form("highest")):
    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        if "youtu.be/" in url:
            video_id = url.split("youtu.be/")[-1].split("?")[0]
            url = f"https://www.youtube.com/watch?v={video_id}"

        yt = YouTube(url)

        # Select stream
        if quality == "highest":
            stream = yt.streams.get_highest_resolution()
        elif quality == "audio":
            stream = yt.streams.get_audio_only()
        else:
            stream = yt.streams.filter(res=quality, progressive=True).first() or yt.streams.get_highest_resolution()

        if not stream:
            raise HTTPException(status_code=400, detail="No stream found")

        # Temporary download
        temp_dir = tempfile.gettempdir()
        filename = f"{uuid.uuid4()}_{yt.title}.{stream.subtype}"
        filepath = os.path.join(temp_dir, filename)

        # Download safely
        stream.download(filename=filepath)

        return FileResponse(
            path=filepath,
            filename=f"{yt.title}.{stream.subtype}",
            media_type=f"video/{stream.subtype}",
            headers={"Content-Disposition": f"attachment; filename={yt.title}.{stream.subtype}"}
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to download: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
