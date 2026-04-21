import sys
import os

# Add jmcomic source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'jmcomic', 'src'))

import io
import time
import traceback
from typing import Optional, List
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed

import json
import shutil
import zipfile
import math
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query, Response, BackgroundTasks, Depends, Header, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import jmcomic
from jmcomic import (
    JmModuleConfig,
    JmcomicText,
    JmImageTool,
)
import site_store

# ---------------------------------------------------------------------------
# Global jmcomic client (created once at startup)
# ---------------------------------------------------------------------------
_client = None

# 章节缓存目录
CACHE_DIR = Path("./chapter_cache")
CACHE_DIR.mkdir(exist_ok=True)


def get_chapter_cache_dir(album_id: str, photo_id: str) -> Path:
    return CACHE_DIR / album_id / photo_id


# 缓存下载状态跟踪 {photo_id: {status, progress, total, error}}
_cache_status: dict = {}
_pdf_status: dict = {}
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}


def normalize_image_suffix(suffix: str) -> str:
    suffix = suffix.lower().lstrip('.')
    return suffix if f'.{suffix}' in IMAGE_EXTENSIONS else 'jpg'


def has_cached_images(cache_dir: Path) -> bool:
    if not cache_dir.exists():
        return False
    return any(
        item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS
        for item in cache_dir.iterdir()
    )


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
        site_store.init_site_storage()
        print("[backend] site storage initialized")
    except Exception as e:
        print(f"[backend] site storage init failed: {e}")
        raise

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


def _download_chapter_background(album_id: str, photo_id: str):
    """后台任务：下载并解码整个章节到磁盘缓存"""
    try:
        cl = get_client()
        photo = cl.get_photo_detail(photo_id, fetch_album=True, fetch_scramble_id=True)
        total = len(photo)
        cache_dir = get_chapter_cache_dir(album_id, photo_id)
        cache_dir.mkdir(parents=True, exist_ok=True)

        _cache_status[photo_id] = {'status': 'downloading', 'progress': 0, 'total': total, 'album_id': album_id}

        for i in range(total):
            image_detail = photo.create_image_detail(i)
            img_url = image_detail.download_url
            scramble_id = int(image_detail.scramble_id) if image_detail.scramble_id else None

            resp = cl.get_jm_image(img_url)
            resp.require_success()

            suffix = normalize_image_suffix(image_detail.img_file_suffix or '')

            if scramble_id and not cl.img_is_not_need_to_decode(img_url, resp):
                from PIL import Image as PILImage
                num = JmImageTool.get_num_by_url(scramble_id, img_url)
                img_src = JmImageTool.open_image(resp.content)
                if num > 0:
                    out_path = cache_dir / f"{i:04d}.jpg"
                    w, h = img_src.size
                    img_decode = PILImage.new("RGB", (w, h))
                    over = h % num
                    for j in range(num):
                        move = math.floor(h / num)
                        y_src = h - (move * (j + 1)) - over
                        y_dst = move * j
                        if j == 0:
                            move += over
                        else:
                            y_dst += over
                        img_decode.paste(
                            img_src.crop((0, y_src, w, y_src + move)),
                            (0, y_dst, w, y_dst + move),
                        )
                    img_decode.save(str(out_path), format="JPEG", quality=92)
                else:
                    out_path = cache_dir / f"{i:04d}.{suffix}"
                    out_path.write_bytes(resp.content)
            else:
                # GIF 或无需解码
                out_path = cache_dir / f"{i:04d}.{suffix}"
                out_path.write_bytes(resp.content)

            _cache_status[photo_id]['progress'] = round((i + 1) / total * 100)

        _cache_status[photo_id]['status'] = 'ready'
        _cache_status[photo_id]['progress'] = 100

    except Exception as e:
        traceback.print_exc()
        _cache_status[photo_id] = {'status': 'error', 'progress': 0, 'error': str(e)}


def _generate_pdf_background(album_id: str, photo_id: str):
    """后台任务：下载图片并生成 PDF"""
    try:
        import img2pdf

        cache_dir = get_chapter_cache_dir(album_id, photo_id)

        # Phase 1: 确保图片已缓存（直接调用，阻塞直到完成）
        _pdf_status[photo_id] = {'status': 'caching', 'progress': 0}

        if _cache_status.get(photo_id, {}).get('status') != 'ready':
            _download_chapter_background(album_id, photo_id)

        if _cache_status.get(photo_id, {}).get('status') != 'ready':
            _pdf_status[photo_id] = {'status': 'error', 'progress': 0, 'error': '图片缓存失败'}
            return

        # Phase 2: 合成 PDF
        _pdf_status[photo_id] = {'status': 'converting', 'progress': 90}

        img_files = sorted(cache_dir.glob('*.jpg')) + sorted(cache_dir.glob('*.jpeg')) \
                    + sorted(cache_dir.glob('*.png')) + sorted(cache_dir.glob('*.webp'))
        # 按文件名（序号）排序，排除 pdf 文件本身
        img_files = sorted(
            [p for p in set(img_files) if p.suffix.lower() != '.pdf'],
            key=lambda p: p.name
        )

        if not img_files:
            _pdf_status[photo_id] = {'status': 'error', 'progress': 0, 'error': '无可用图片'}
            return

        pdf_path = cache_dir / f"{photo_id}.pdf"
        with open(str(pdf_path), 'wb') as f:
            f.write(img2pdf.convert([str(p) for p in img_files]))

        _pdf_status[photo_id] = {'status': 'ready', 'progress': 100}

    except ImportError:
        _pdf_status[photo_id] = {'status': 'error', 'progress': 0, 'error': '请安装 img2pdf: pip install img2pdf'}
    except Exception as e:
        traceback.print_exc()
        _pdf_status[photo_id] = {'status': 'error', 'progress': 0, 'error': str(e)}


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
    """Get ranking: all / day / week / month."""
    try:
        cl = get_client()
        if ranking_type == "all":
            result = cl.categories_filter(page, 'a', category, 'mv')
        elif ranking_type == "day":
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
            from PIL import Image

            num = JmImageTool.get_num_by_url(scramble_id, img_url)
            img_src = JmImageTool.open_image(resp.content)

            if num == 0:
                # No decoding needed
                buf = io.BytesIO()
                img_src.save(buf, format="JPEG", quality=92)
                return Response(content=buf.getvalue(), media_type="image/jpeg")

            # In-memory decode (replicate decode_and_save logic)
            w, h = img_src.size
            img_decode = Image.new("RGB", (w, h))
            over = h % num
            for i in range(num):
                move = math.floor(h / num)
                y_src = h - (move * (i + 1)) - over
                y_dst = move * i
                if i == 0:
                    move += over
                else:
                    y_dst += over
                img_decode.paste(
                    img_src.crop((0, y_src, w, y_src + move)),
                    (0, y_dst, w, y_dst + move),
                )

            buf = io.BytesIO()
            img_decode.save(buf, format="JPEG", quality=92)
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
    username: str = Field(..., min_length=3, max_length=64)
    password: str


@app.post("/api/auth/login")
def login(body: LoginRequest):
    result = site_store.authenticate_user(body.username, body.password)
    if not result:
        raise HTTPException(401, "登录失败")
    return {"ok": True, **result}


@app.post("/api/auth/logout")
def logout(
    _: dict = Depends(site_store.require_current_user),
    authorization: Optional[str] = Header(None),
):
    token = site_store.extract_token(authorization)
    if token:
        site_store.delete_session(token)
    return {"ok": True}


@app.get("/api/auth/me")
def auth_me(current_user: dict = Depends(site_store.require_current_user)):
    return {"user": current_user}


@app.post("/api/users/me/avatar")
async def upload_my_avatar(
    avatar: UploadFile = File(...),
    current_user: dict = Depends(site_store.require_current_user),
):
    if not avatar.content_type or not avatar.content_type.startswith("image/"):
        raise HTTPException(400, "只支持图片文件")
    content = await avatar.read()
    user = site_store.set_user_avatar(current_user["id"], content)
    return {"ok": True, "user": user}


@app.get("/api/users/{user_id}/avatar")
def get_user_avatar(user_id: int):
    avatar_path = site_store.get_avatar_path(user_id)
    if not avatar_path.exists():
        raise HTTPException(404, "头像不存在")
    return FileResponse(str(avatar_path), media_type="image/jpeg")


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    is_admin: bool = False


class UpdateUserRequest(BaseModel):
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=6, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=6, max_length=128)


@app.get("/api/admin/users")
def admin_users(_: dict = Depends(site_store.require_admin_user)):
    return {"items": site_store.list_users()}


@app.post("/api/admin/users")
def admin_create_user(
    body: CreateUserRequest,
    _: dict = Depends(site_store.require_admin_user),
):
    user = site_store.create_user(body.username, body.password, body.is_admin)
    return {"ok": True, "user": user}


@app.patch("/api/admin/users/{user_id}")
def admin_update_user(
    user_id: int,
    body: UpdateUserRequest,
    current_user: dict = Depends(site_store.require_admin_user),
):
    user = site_store.update_user(
        current_user["id"],
        user_id,
        is_admin=body.is_admin,
        is_active=body.is_active,
    )
    return {"ok": True, "user": user}


@app.post("/api/admin/users/{user_id}/reset-password")
def admin_reset_password(
    user_id: int,
    body: ResetPasswordRequest,
    current_user: dict = Depends(site_store.require_admin_user),
):
    user = site_store.reset_user_password(current_user["id"], user_id, body.new_password)
    return {"ok": True, "user": user}


@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(
    user_id: int,
    current_user: dict = Depends(site_store.require_admin_user),
):
    site_store.delete_user(current_user["id"], user_id)
    return {"ok": True}


@app.post("/api/auth/change-password")
def auth_change_password(
    body: ChangePasswordRequest,
    current_user: dict = Depends(site_store.require_current_user),
):
    user = site_store.change_password(
        current_user["id"],
        body.current_password,
        body.new_password,
    )
    return {"ok": True, "user": user}


# ---- Favorites ----

@app.get("/api/favorites")
def favorites(
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    folder_id: str = Query("0"),
    order_by: str = Query("mr"),
    current_user: dict = Depends(site_store.require_current_user),
):
    data = site_store.list_favorites(current_user["id"], page, page_size)
    data["folders"] = []
    return data


class FavoriteRequest(BaseModel):
    album_id: str
    folder_id: str = "0"
    title: str = ""
    author: str = ""
    cover: str = ""


@app.get("/api/favorites/{album_id}/status")
def favorite_status(
    album_id: str,
    current_user: dict = Depends(site_store.require_current_user),
):
    return site_store.get_favorite_status(current_user["id"], album_id)


@app.post("/api/favorites")
def add_favorite(
    body: FavoriteRequest,
    current_user: dict = Depends(site_store.require_current_user),
):
    item = site_store.add_favorite(
        current_user["id"],
        body.album_id,
        title=body.title,
        author=body.author,
        cover=body.cover,
    )
    return {"ok": True, "item": item}


@app.delete("/api/favorites/{album_id}")
def delete_favorite(
    album_id: str,
    current_user: dict = Depends(site_store.require_current_user),
):
    removed = site_store.remove_favorite(current_user["id"], album_id)
    if not removed:
        raise HTTPException(404, "收藏不存在")
    return {"ok": True}


# ---- History / Reading ----

class HistoryRequest(BaseModel):
    album_id: str
    title: str = ""
    album_title: str = ""
    comic_title: str = ""
    author: str = ""
    cover: str = ""


class ReadingProgressRequest(BaseModel):
    album_id: str
    photo_id: str
    album_title: str = ""
    comic_title: str = ""
    album_author: str = ""
    author: str = ""
    cover: str = ""
    chapter_title: str = ""
    chapter_sort: Optional[int] = None
    sort: Optional[int] = None
    page_index: Optional[int] = Field(None, ge=0)
    current_page: Optional[int] = Field(None, ge=0)
    page: Optional[int] = Field(None, ge=0)
    last_page: int = Field(0, ge=0)
    total_pages: int = Field(0, ge=0)


@app.get("/api/history")
def get_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    current_user: dict = Depends(site_store.require_current_user),
):
    return site_store.list_history(current_user["id"], page, page_size)


@app.post("/api/history")
def upsert_history(
    body: HistoryRequest,
    current_user: dict = Depends(site_store.require_current_user),
):
    item = site_store.upsert_history(
        current_user["id"],
        body.album_id,
        title=body.title or body.album_title or body.comic_title,
        author=body.author,
        cover=body.cover,
    )
    return {"ok": True, "item": item}


@app.delete("/api/history")
def delete_all_history(current_user: dict = Depends(site_store.require_current_user)):
    return site_store.clear_history(current_user["id"])


@app.delete("/api/history/{album_id}")
def delete_history_item(
    album_id: str,
    current_user: dict = Depends(site_store.require_current_user),
):
    removed = site_store.remove_history(current_user["id"], album_id)
    if not removed:
        raise HTTPException(404, "历史记录不存在")
    return {"ok": True}


@app.get("/api/reading/{album_id}")
def get_reading_state(
    album_id: str,
    current_user: dict = Depends(site_store.require_current_user),
):
    return site_store.get_reading_state(current_user["id"], album_id)


@app.post("/api/reading/progress")
def save_reading_progress(
    body: ReadingProgressRequest,
    current_user: dict = Depends(site_store.require_current_user),
):
    item = site_store.save_reading_progress(
        current_user["id"],
        body.album_id,
        body.photo_id,
        album_title=body.album_title or body.comic_title,
        album_author=body.album_author or body.author,
        cover=body.cover,
        chapter_title=body.chapter_title,
        chapter_sort=body.chapter_sort if body.chapter_sort is not None else body.sort,
        last_page=body.last_page or body.current_page or body.page or ((body.page_index + 1) if body.page_index is not None else 0),
        total_pages=body.total_pages,
    )
    return {"ok": True, "item": item}


# ---- Comment ----

class CommentRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    parent_id: Optional[int] = None


@app.get("/api/comments/{album_id}")
def get_comments(
    album_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(site_store.require_current_user),
):
    return site_store.list_comments(
        album_id,
        page,
        page_size,
        viewer_user_id=current_user["id"],
        viewer_is_admin=current_user["is_admin"],
    )


@app.post("/api/comments/{album_id}")
def post_comment(
    album_id: str,
    body: CommentRequest,
    current_user: dict = Depends(site_store.require_current_user),
):
    item = site_store.create_comment(
        current_user["id"],
        album_id,
        body.content,
        body.parent_id,
    )
    return {"ok": True, "item": item}


@app.delete("/api/comments/{comment_id}")
def delete_comment(
    comment_id: int,
    current_user: dict = Depends(site_store.require_current_user),
):
    site_store.delete_comment(comment_id, current_user["id"], current_user["is_admin"])
    return {"ok": True}


# ---- Chapter Cache ----

@app.get("/api/cache/library")
def get_cache_library(current_user: dict = Depends(site_store.require_current_user)):
    """扫描磁盘，返回所有已缓存的专辑和章节信息"""
    albums = {}
    total_size = 0

    user_cache_map = site_store.get_user_cache_album_map(current_user["id"])

    if not CACHE_DIR.exists() or not user_cache_map:
        return {"albums": {}, "total_size_bytes": 0}

    for album_dir in sorted(CACHE_DIR.iterdir()):
        if not album_dir.is_dir():
            continue
        album_id = album_dir.name
        allowed_photo_ids = user_cache_map.get(album_id)
        if not allowed_photo_ids:
            continue
        chapters = {}
        album_size = 0

        # 读取专辑标题
        album_meta_file = album_dir / 'meta.json'
        album_title = ""
        album_author = ""
        if album_meta_file.exists():
            try:
                _data = json.loads(album_meta_file.read_text(encoding='utf-8'))
                album_title = _data.get('title', '')
                album_author = _data.get('author', '')
            except Exception:
                pass

        for chapter_dir in sorted(album_dir.iterdir()):
            if not chapter_dir.is_dir():
                continue
            photo_id = chapter_dir.name
            if photo_id not in allowed_photo_ids:
                continue

            # 读取章节标题
            chapter_meta_file = chapter_dir / 'meta.json'
            chapter_title = ""
            if chapter_meta_file.exists():
                try:
                    chapter_title = json.loads(chapter_meta_file.read_text(encoding='utf-8')).get('title', '')
                except Exception:
                    pass

            # 统计图片数和大小
            image_files = [f for f in chapter_dir.iterdir()
                           if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS]
            pdf_file = chapter_dir / f"{photo_id}.pdf"
            has_pdf = pdf_file.exists()

            chapter_size = sum(f.stat().st_size for f in chapter_dir.iterdir() if f.is_file())
            mtime = chapter_dir.stat().st_mtime

            chapters[photo_id] = {
                "chapter_title": chapter_title,
                "image_count": len(image_files),
                "has_pdf": has_pdf,
                "size_bytes": chapter_size,
                "mtime": mtime,
            }
            album_size += chapter_size

        if chapters:
            albums[album_id] = {
                "album_title": album_title,
                "author": album_author,
                "chapters": chapters,
                "chapter_count": len(chapters),
                "total_size_bytes": album_size,
            }
            total_size += album_size

    return {"albums": albums, "total_size_bytes": total_size}


@app.delete("/api/cache/{album_id}/{photo_id}")
def delete_chapter_cache(
    album_id: str,
    photo_id: str,
    current_user: dict = Depends(site_store.require_current_user),
):
    """删除单个章节的缓存"""
    cache_dir = get_chapter_cache_dir(album_id, photo_id)
    removed = site_store.remove_user_cache_item(current_user["id"], album_id, photo_id)
    if not removed:
        raise HTTPException(404, "缓存记录不存在")
    try:
        shared = site_store.count_cache_links(album_id, photo_id) > 0
        if not shared and cache_dir.exists():
            shutil.rmtree(str(cache_dir))
            _cache_status.pop(photo_id, None)
            _pdf_status.pop(photo_id, None)
        # 若专辑目录空了则一并删除
            album_dir = CACHE_DIR / album_id
            if album_dir.exists() and not any(album_dir.iterdir()):
                album_dir.rmdir()
        return {"ok": True, "shared": shared}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.delete("/api/cache/{album_id}")
def delete_album_cache(
    album_id: str,
    current_user: dict = Depends(site_store.require_current_user),
):
    """删除整个专辑的缓存"""
    album_dir = CACHE_DIR / album_id
    photo_ids = site_store.remove_user_album_cache_items(current_user["id"], album_id)
    if not photo_ids:
        raise HTTPException(404, "缓存记录不存在")
    try:
        # 清理内存状态：仅清理属于该专辑的条目
        photo_ids = list(photo_ids)
        for photo_id in photo_ids:
            if site_store.count_cache_links(album_id, photo_id) > 0:
                continue
            _cache_status.pop(photo_id, None)
            _pdf_status.pop(photo_id, None)
            chapter_dir = get_chapter_cache_dir(album_id, photo_id)
            if chapter_dir.exists():
                shutil.rmtree(str(chapter_dir))
        if album_dir.exists() and not any(album_dir.iterdir()):
            shutil.rmtree(str(album_dir))
        return {"ok": True}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/cache/queue")
def get_cache_queue(current_user: dict = Depends(site_store.require_current_user)):
    """返回所有缓存任务的实时状态（仅内存中的记录）"""
    queue = []
    allowed_photo_ids = site_store.get_user_cache_photo_ids(current_user["id"])
    for photo_id, info in _cache_status.items():
        if photo_id not in allowed_photo_ids:
            continue
        queue.append({
            'photo_id': photo_id,
            'album_id': info.get('album_id', ''),
            'status': info.get('status', 'unknown'),
            'progress': info.get('progress', 0),
        })
    # 按状态排序：进行中 > 等待 > 完成 > 错误
    order = {'downloading': 0, 'pending': 1, 'ready': 2, 'error': 3}
    queue.sort(key=lambda x: order.get(x['status'], 9))
    return {'queue': queue}


@app.delete("/api/cache/queue/completed")
def clear_completed_cache():
    """清除内存中已完成（ready/error）的缓存记录"""
    to_remove = [pid for pid, info in _cache_status.items()
                 if info.get('status') in ('ready', 'error')]
    for pid in to_remove:
        _cache_status.pop(pid, None)
    return {'cleared': len(to_remove)}


class CacheMetaBody(BaseModel):
    album_title: str = ""
    author: str = ""
    chapter_title: str = ""


@app.post("/api/chapters/{album_id}/{photo_id}/cache")
def start_chapter_cache(
    album_id: str,
    photo_id: str,
    background_tasks: BackgroundTasks,
    meta: CacheMetaBody = None,
    current_user: dict = Depends(site_store.require_current_user),
):
    cache_dir = get_chapter_cache_dir(album_id, photo_id)
    current = _cache_status.get(photo_id, {})
    site_store.add_user_cache_item(current_user["id"], album_id, photo_id)

    if current.get('status') == 'downloading':
        return {"status": "downloading", "progress": current.get('progress', 0)}

    if current.get('status') == 'ready' and has_cached_images(cache_dir):
        return {"status": "ready", "progress": 100}

    if has_cached_images(cache_dir):
        _cache_status[photo_id] = {'status': 'ready', 'progress': 100, 'album_id': album_id}
        return {"status": "ready", "progress": 100}

    # 持久化元数据到磁盘
    if meta:
        album_dir = CACHE_DIR / album_id
        album_dir.mkdir(parents=True, exist_ok=True)
        if meta.album_title:
            album_meta = album_dir / 'meta.json'
            try:
                existing = json.loads(album_meta.read_text(encoding='utf-8')) if album_meta.exists() else {}
            except Exception:
                existing = {}
            existing['title'] = meta.album_title
            if meta.author:
                existing['author'] = meta.author
            album_meta.write_text(json.dumps(existing, ensure_ascii=False), encoding='utf-8')

        if meta.chapter_title:
            cache_dir.mkdir(parents=True, exist_ok=True)
            (cache_dir / 'meta.json').write_text(
                json.dumps({'title': meta.chapter_title}, ensure_ascii=False),
                encoding='utf-8'
            )

    _cache_status[photo_id] = {'status': 'pending', 'progress': 0, 'album_id': album_id}
    background_tasks.add_task(_download_chapter_background, album_id, photo_id)
    return {"status": "pending", "progress": 0}


@app.get("/api/chapters/{album_id}/{photo_id}/cache/status")
def get_chapter_cache_status(
    album_id: str,
    photo_id: str,
    current_user: dict = Depends(site_store.require_current_user),
):
    if not site_store.has_user_cache_item(current_user["id"], album_id, photo_id):
        return {"status": "not_started", "progress": 0}
    current = _cache_status.get(photo_id)
    if current:
        return {"status": current['status'], "progress": current.get('progress', 0)}
    cache_dir = get_chapter_cache_dir(album_id, photo_id)
    if has_cached_images(cache_dir):
        _cache_status[photo_id] = {'status': 'ready', 'progress': 100, 'album_id': album_id}
        return {"status": "ready", "progress": 100}
    return {"status": "not_started", "progress": 0}


@app.get("/api/chapters/{album_id}/{photo_id}/cached/{index}")
def get_cached_image(album_id: str, photo_id: str, index: int):
    cache_dir = get_chapter_cache_dir(album_id, photo_id)
    if not cache_dir.exists():
        raise HTTPException(404, "Chapter not cached")
    matches = sorted(cache_dir.glob(f"{index:04d}.*"))
    if not matches:
        raise HTTPException(404, f"Image {index} not found in cache")
    file_path = matches[0]
    suffix = file_path.suffix.lower()
    media_map = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
                 '.gif': 'image/gif', '.webp': 'image/webp'}
    return FileResponse(str(file_path), media_type=media_map.get(suffix, 'image/jpeg'))


@app.get("/api/comics/{album_id}/cache/status")
def get_album_cache_status(
    album_id: str,
    current_user: dict = Depends(site_store.require_current_user),
):
    """一次性返回该漫画所有已缓存/缓存中章节的状态

    只返回有缓存记录的章节（磁盘有目录 或 内存有状态），
    未触发过的章节不出现在结果中（前端视为 not_started）。
    返回格式：{ photo_id: { status, progress } }
    """
    result = {}
    album_dir = CACHE_DIR / album_id
    allowed_photo_ids = site_store.get_user_cache_photo_ids(current_user["id"], album_id)

    if not allowed_photo_ids:
        return result

    # 先扫描磁盘：章节目录存在且有图片 → ready
    if album_dir.exists():
        for chapter_dir in album_dir.iterdir():
            if not chapter_dir.is_dir():
                continue
            photo_id = chapter_dir.name
            if photo_id in allowed_photo_ids and has_cached_images(chapter_dir):
                result[photo_id] = {'status': 'ready', 'progress': 100}

    # 用内存状态覆盖（内存更实时，能反映正在下载的进度）
    for photo_id, mem in _cache_status.items():
        if mem.get('album_id') == album_id and photo_id in allowed_photo_ids:
            result[photo_id] = {
                'status': mem.get('status', 'pending'),
                'progress': mem.get('progress', 0),
            }

    return result


# ---- Chapter PDF ----

@app.post("/api/chapters/{album_id}/{photo_id}/pdf")
def start_chapter_pdf(album_id: str, photo_id: str, background_tasks: BackgroundTasks):
    current = _pdf_status.get(photo_id, {})
    if current.get('status') in ('caching', 'converting'):
        return {"status": current['status'], "progress": current.get('progress', 0)}
    if current.get('status') == 'ready':
        pdf_path = get_chapter_cache_dir(album_id, photo_id) / f"{photo_id}.pdf"
        if pdf_path.exists():
            return {"status": "ready", "progress": 100}
    _pdf_status[photo_id] = {'status': 'caching', 'progress': 0}
    background_tasks.add_task(_generate_pdf_background, album_id, photo_id)
    return {"status": "caching", "progress": 0}


@app.get("/api/chapters/{album_id}/{photo_id}/pdf/status")
def get_chapter_pdf_status(album_id: str, photo_id: str):
    pdf = _pdf_status.get(photo_id, {})
    if not pdf:
        pdf_path = get_chapter_cache_dir(album_id, photo_id) / f"{photo_id}.pdf"
        if pdf_path.exists():
            return {"status": "ready", "progress": 100, "phase": "ready"}
        return {"status": "not_started", "progress": 0, "phase": ""}
    status = pdf.get('status', 'caching')
    if status == 'caching':
        cache_progress = _cache_status.get(photo_id, {}).get('progress', 0)
        return {"status": "caching", "progress": round(cache_progress * 0.9), "phase": "caching"}
    return {"status": status, "progress": pdf.get('progress', 0), "phase": status}


@app.get("/api/chapters/{album_id}/{photo_id}/pdf/download")
def download_chapter_pdf(album_id: str, photo_id: str):
    pdf_path = get_chapter_cache_dir(album_id, photo_id) / f"{photo_id}.pdf"
    if not pdf_path.exists():
        raise HTTPException(404, "PDF 尚未生成")
    return FileResponse(
        str(pdf_path),
        media_type="application/pdf",
        filename=f"JMComic_{photo_id}.pdf",
        headers={"Content-Disposition": f"attachment; filename=JMComic_{photo_id}.pdf"}
    )


# ---- Domain Management ----

@app.get("/api/domains")
def get_domains():
    """Get current domain list."""
    try:
        cl = get_client()
        return {"domains": cl.get_domain_list()}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, str(e))


class DomainRequest(BaseModel):
    domains: list


@app.put("/api/domains")
def set_domains(body: DomainRequest):
    """Set domain list."""
    try:
        cl = get_client()
        cl.set_domain_list(body.domains)
        return {"ok": True, "domains": cl.get_domain_list()}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, str(e))


@app.get("/api/domains/discover")
def discover_domains():
    """Discover all available domains."""
    try:
        cl = get_client()
        html_domain = cl.get_html_domain()
        all_domains = cl.get_html_domain_all()
        return {
            "current": html_domain,
            "available": all_domains,
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, str(e))


def _ping_domain(domain: str, timeout: float = 8.0) -> dict:
    """Ping a single domain and return latency info."""
    from curl_cffi import requests as curl_requests
    url = f"https://{domain}"
    try:
        start = time.time()
        resp = curl_requests.get(
            url,
            timeout=timeout,
            impersonate="chrome",
            allow_redirects=False,
        )
        latency = round((time.time() - start) * 1000)
        return {"domain": domain, "latency": latency, "status": "ok"}
    except Exception as e:
        return {"domain": domain, "latency": -1, "status": "error", "error": str(e)}


@app.get("/api/domains/ping")
def ping_domains():
    """Test latency for all known domains."""
    try:
        cl = get_client()
        current_domains = cl.get_domain_list()
        # Also try to discover more domains
        all_domains = set(current_domains)
        try:
            discovered = cl.get_html_domain_all()
            if discovered:
                all_domains.update(discovered)
        except Exception:
            pass

        results = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(_ping_domain, d): d for d in all_domains}
            for future in as_completed(futures):
                results.append(future.result())

        results.sort(key=lambda x: (x["latency"] < 0, x["latency"]))
        return {
            "current": current_domains,
            "results": results,
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, str(e))


class SwitchDomainRequest(BaseModel):
    domain: str


@app.post("/api/domains/switch")
def switch_domain(body: SwitchDomainRequest):
    """Switch to a specific domain by putting it first in the list."""
    try:
        cl = get_client()
        current = cl.get_domain_list()
        new_list = [body.domain] + [d for d in current if d != body.domain]
        cl.set_domain_list(new_list)
        return {"ok": True, "domains": cl.get_domain_list()}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, str(e))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
