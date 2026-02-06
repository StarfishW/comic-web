import sys
import os

# Add jmcomic source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'jmcomic', 'src'))

import io
import traceback
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import jmcomic
from jmcomic import (
    JmModuleConfig,
    JmcomicText,
    JmImageTool,
)

# ---------------------------------------------------------------------------
# Global jmcomic client (created once at startup)
# ---------------------------------------------------------------------------
_client = None


def get_client():
    global _client
    if _client is None:
        option = JmModuleConfig.option_class().default()
        _client = option.new_jm_client()
        _client.set_cache_dict({})
    return _client


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: warm up the client
    try:
        get_client()
        print("[backend] jmcomic client initialized")
    except Exception as e:
        print(f"[backend] client init warning: {e}")
    yield
    # Shutdown
    print("[backend] shutting down")


app = FastAPI(title="JMComic API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helper: serialize entities to dicts
# ---------------------------------------------------------------------------

def album_brief(album_id: str, info: dict) -> dict:
    """Convert search/category page item to a brief dict."""
    return {
        "id": str(album_id),
        "title": info.get("name", ""),
        "tags": info.get("tags", []),
        "author": info.get("author", ""),
        "cover": JmcomicText.get_album_cover_url(album_id),
    }


def album_detail_to_dict(album) -> dict:
    episodes = []
    for pid, sort, title in album.episode_list:
        episodes.append({"id": str(pid), "sort": sort, "title": title})
    return {
        "id": str(album.album_id),
        "title": album.name,
        "author": album.author,
        "authors": getattr(album, 'authors', []),
        "description": getattr(album, 'description', '') or '',
        "tags": album.tags if isinstance(album.tags, list) else [],
        "actors": getattr(album, 'actors', []),
        "works": getattr(album, 'works', []),
        "likes": getattr(album, 'likes', '0'),
        "views": getattr(album, 'views', '0'),
        "comment_count": getattr(album, 'comment_count', 0),
        "pub_date": getattr(album, 'pub_date', ''),
        "update_date": getattr(album, 'update_date', ''),
        "page_count": getattr(album, 'page_count', 0),
        "episodes": episodes,
        "cover": JmcomicText.get_album_cover_url(album.album_id),
        "related_list": getattr(album, 'related_list', []) or [],
    }


def photo_detail_to_dict(photo) -> dict:
    images = []
    for i in range(len(photo)):
        img = photo.create_image_detail(i)
        images.append({
            "index": i,
            "filename": img.filename,
            "url": f"/api/chapters/{photo.photo_id}/images/{i}",
        })
    return {
        "id": str(photo.photo_id),
        "title": photo.name,
        "album_id": str(photo.album_id),
        "album_index": photo.album_index,
        "page_count": len(photo),
        "scramble_id": str(photo.scramble_id) if photo.scramble_id else None,
        "tags": photo.tags if isinstance(photo.tags, list) else [],
        "images": images,
    }


def page_content_to_dict(page_content) -> dict:
    items = []
    for aid, info in page_content.content:
        items.append(album_brief(aid, info))
    return {
        "items": items,
        "total": int(page_content.total),
        "page_count": page_content.page_count,
    }


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

# ---- Browse / Category ----

@app.get("/api/comics")
def list_comics(
    page: int = Query(1, ge=1),
    order_by: str = Query("mr"),  # mr=latest, mv=views
    time: str = Query("a"),       # a=all, m=month, w=week, t=today
    category: str = Query("0"),   # 0=all
):
    """List comics with filters (categories_filter)."""
    try:
        cl = get_client()
        result = cl.categories_filter(
            page=page,
            time=time,
            category=category,
            order_by=order_by,
        )
        return page_content_to_dict(result)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, str(e))


@app.get("/api/ranking/{ranking_type}")
def ranking(
    ranking_type: str,
    page: int = Query(1, ge=1),
    category: str = Query("0"),
):
    """Get ranking: day / week / month."""
    try:
        cl = get_client()
        if ranking_type == "day":
            result = cl.day_ranking(page, category)
        elif ranking_type == "week":
            result = cl.week_ranking(page, category)
        elif ranking_type == "month":
            result = cl.month_ranking(page, category)
        else:
            raise HTTPException(400, f"Invalid ranking type: {ranking_type}")
        return page_content_to_dict(result)
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, str(e))


# ---- Search ----

@app.get("/api/search")
def search(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    main_tag: int = Query(0),     # 0=site,1=work,2=author,3=tag,4=actor
    order_by: str = Query("mr"),
    time: str = Query("a"),
    category: str = Query("0"),
):
    """Search comics."""
    try:
        cl = get_client()
        result = cl.search(
            search_query=q,
            page=page,
            main_tag=main_tag,
            order_by=order_by,
            time=time,
            category=category,
            sub_category=None,
        )
        return page_content_to_dict(result)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, str(e))


# ---- Comic Detail ----

@app.get("/api/comics/{album_id}")
def comic_detail(album_id: str):
    """Get full album detail."""
    try:
        cl = get_client()
        album = cl.get_album_detail(album_id)
        return album_detail_to_dict(album)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, str(e))


@app.get("/api/comics/{album_id}/cover")
def comic_cover(album_id: str, size: str = Query("")):
    """Proxy album cover image."""
    try:
        cl = get_client()
        url = JmcomicText.get_album_cover_url(album_id, size=size)
        resp = cl.get_jm_image(url)
        resp.require_success()
        content_type = "image/jpeg"
        if url.endswith(".png"):
            content_type = "image/png"
        elif url.endswith(".webp"):
            content_type = "image/webp"
        return Response(content=resp.content, media_type=content_type)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, str(e))


# ---- Chapter / Photo ----

@app.get("/api/chapters/{photo_id}")
def chapter_detail(photo_id: str):
    """Get chapter detail with image list."""
    try:
        cl = get_client()
        photo = cl.get_photo_detail(photo_id, fetch_album=True, fetch_scramble_id=True)
        return photo_detail_to_dict(photo)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, str(e))


@app.get("/api/chapters/{photo_id}/images/{index}")
def chapter_image(photo_id: str, index: int):
    """Serve a decoded comic image."""
    try:
        cl = get_client()
        photo = cl.get_photo_detail(photo_id, fetch_album=True, fetch_scramble_id=True)
        if index < 0 or index >= len(photo):
            raise HTTPException(404, "Image index out of range")

        image_detail = photo.create_image_detail(index)
        img_url = image_detail.download_url
        scramble_id = int(image_detail.scramble_id) if image_detail.scramble_id else None

        # Download the image
        resp = cl.get_jm_image(img_url)
        resp.require_success()

        # Decode if needed
        if scramble_id and not cl.img_is_not_need_to_decode(img_url, resp):
            num = JmImageTool.get_num_by_url(scramble_id, img_url)
            img = JmImageTool.open_image(resp.content)
            img = JmImageTool.decode_image(num, img)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=92)
            return Response(content=buf.getvalue(), media_type="image/jpeg")
        else:
            # GIF or no-decode needed
            suffix = image_detail.img_file_suffix.lower()
            media = "image/jpeg"
            if suffix in (".png",):
                media = "image/png"
            elif suffix in (".gif",):
                media = "image/gif"
            elif suffix in (".webp",):
                media = "image/webp"
            return Response(content=resp.content, media_type=media)
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, str(e))


# ---- User / Auth ----

class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/api/auth/login")
def login(body: LoginRequest):
    """Login and store session."""
    try:
        cl = get_client()
        cl.login(body.username, body.password)
        return {"ok": True, "message": "Login successful"}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(401, str(e))


# ---- Favorites ----

@app.get("/api/favorites")
def favorites(
    page: int = Query(1, ge=1),
    folder_id: str = Query("0"),
    order_by: str = Query("mr"),
):
    """Get user favorite albums."""
    try:
        cl = get_client()
        result = cl.favorite_folder(page=page, folder_id=folder_id, order_by=order_by)
        data = page_content_to_dict(result)
        # Add folder list
        folders = []
        for fid, fname in result.iter_folder_id_name():
            folders.append({"id": fid, "name": fname})
        data["folders"] = folders
        return data
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, str(e))


class FavoriteRequest(BaseModel):
    album_id: str
    folder_id: str = "0"


@app.post("/api/favorites")
def add_favorite(body: FavoriteRequest):
    """Add album to favorites."""
    try:
        cl = get_client()
        cl.add_favorite_album(body.album_id, body.folder_id)
        return {"ok": True}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, str(e))


# ---- Comment ----

class CommentRequest(BaseModel):
    video_id: str
    comment: str
    comment_id: Optional[str] = None


@app.post("/api/comments")
def post_comment(body: CommentRequest):
    """Post a comment or reply."""
    try:
        cl = get_client()
        resp = cl.album_comment(
            video_id=body.video_id,
            comment=body.comment,
            comment_id=body.comment_id,
        )
        return {"ok": True}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, str(e))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
