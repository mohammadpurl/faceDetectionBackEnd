from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pathlib import Path
import cv2
import numpy as np
from datetime import datetime
from app.services.auth import get_current_user
from app.models.user import User
from app.services.user_service import insert_user_photo_in_db
import mediapipe as mp
import numpy as np
import os
from typing import List, TypedDict
import base64

router = APIRouter()


def is_blurry(image_np, threshold=50):
    gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F, ksize=5).var()
    return laplacian_var < threshold


def is_frontal_face(image_np, angle_threshold=30):
    mp_face_mesh = mp.solutions.face_mesh
    with mp_face_mesh.FaceMesh(static_image_mode=True) as face_mesh:
        results = face_mesh.process(cv2.cvtColor(image_np, cv2.COLOR_BGR2RGB))
        if not results.multi_face_landmarks:
            return False  # هیچ چهره‌ای پیدا نشد

        # فقط اولین چهره را بررسی می‌کنیم
        face_landmarks = results.multi_face_landmarks[0]
        # نقاط کلیدی چشم چپ و راست و بینی
        left_eye = face_landmarks.landmark[33]
        right_eye = face_landmarks.landmark[263]
        nose_tip = face_landmarks.landmark[1]

        # محاسبه زاویه بین چشم‌ها و بینی (ساده‌شده)
        dx = right_eye.x - left_eye.x
        dy = right_eye.y - left_eye.y
        angle = np.degrees(np.arctan2(dy, dx))

        # افزایش آستانه زاویه برای پذیرش چهره‌های با زاویه بیشتر
        return abs(angle) < angle_threshold


@router.post("/upload-photo/")
async def upload_photo(
    user_id: int,
    current_user: User = Depends(get_current_user),
    file: UploadFile = File(...),
):
    # ذخیره فایل موقت
    contents = await file.read()
    image_np = cv2.imdecode(np.frombuffer(contents, np.uint8), cv2.IMREAD_COLOR)

    # کنترل کیفیت با حساسیت کمتر
    if is_blurry(image_np):
        raise HTTPException(
            status_code=400, detail="عکس کمی تار است، لطفا عکس واضح‌تری انتخاب کنید"
        )
    if not is_frontal_face(image_np):
        raise HTTPException(
            status_code=400, detail="لطفا عکس را با زاویه مناسب‌تری بگیرید"
        )

    if current_user.id != user_id:
        raise HTTPException(
            status_code=400, detail="شما میتوانید فقط عکس خود را آپلود کنید"
        )

    # ایجاد پوشه مخصوص کاربر
    user_dir = Path(f"media/avatars/user_{user_id}")
    user_dir.mkdir(parents=True, exist_ok=True)

    # ذخیره عکس در پوشه کاربر
    filename = f"{int(datetime.now().timestamp())}.jpg"
    file_path = user_dir / filename
    cv2.imwrite(str(file_path), image_np)

    await insert_user_photo_in_db(user_id, str(file_path))

    return {"message": "عکس با موفقیت ذخیره شد", "image_path": str(file_path)}


class ImageInfo(TypedDict):
    filename: str
    path: str
    upload_date: str
    size: int
    timestamp: int
    imageData: str


class ImageResponse(TypedDict):
    filename: str
    path: str
    upload_date: str
    size: int
    imageData: str  # base64 encoded image


@router.get("/images/{user_id}", response_model=List[ImageResponse])
async def get_user_images(
    user_id: int,
    current_user: User = Depends(get_current_user),
):
    """
    دریافت لیست تصاویر کاربر
    """
    if current_user.id != user_id:
        raise HTTPException(
            status_code=400, detail="شما فقط می‌توانید تصاویر خود را مشاهده کنید"
        )

    # مسیر پوشه کاربر
    user_dir = Path(f"media/avatars/user_{user_id}")

    if not user_dir.exists():
        return []

    # دریافت لیست فایل‌های تصویر
    image_files: List[ImageInfo] = []

    # جستجوی همه فایل‌های تصویر در پوشه
    for file in user_dir.glob("*.jpg"):
        try:
            timestamp = int(file.stem)

            # خواندن تصویر و تبدیل به base64
            with open(file, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode("utf-8")

            image_info: ImageInfo = {
                "filename": file.name,
                "path": str(file),
                "upload_date": datetime.fromtimestamp(timestamp).isoformat(),
                "size": file.stat().st_size,
                "timestamp": timestamp,
                "imageData": f"data:image/jpeg;base64,{image_data}",
            }
            image_files.append(image_info)

        except (ValueError, OSError) as e:
            print(f"Error processing file {file.name}: {str(e)}")
            continue

    # مرتب‌سازی بر اساس تاریخ آپلود (نزولی)
    image_files = sorted(image_files, key=lambda x: x["timestamp"], reverse=True)

    # تبدیل به فرمت پاسخ
    response = [
        {
            "filename": img["filename"],
            "path": img["path"],
            "upload_date": img["upload_date"],
            "size": img["size"],
            "imageData": img["imageData"],
        }
        for img in image_files
    ]

    print(f"Found {len(response)} images for user {user_id}")
    return response
