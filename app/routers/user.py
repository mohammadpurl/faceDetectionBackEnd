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

router = APIRouter()


def is_blurry(image_np, threshold=100):
    gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    return laplacian_var < threshold


def is_frontal_face(image_np, angle_threshold=20):
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

        # اگر زاویه خیلی زیاد نباشد، چهره تقریباً رو به دوربین است
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

    # کنترل کیفیت
    if is_blurry(image_np):
        raise HTTPException(status_code=400, detail="عکس تار است")
    if not is_frontal_face(image_np):
        raise HTTPException(status_code=400, detail="چهره باید رو به دوربین باشد")

    if current_user.id != user_id:
        raise HTTPException(
            status_code=400, detail="شما میتوانید فقط عکس خود را آپلود کنید"
        )

    # ذخیره عکس
    save_dir = Path("media/avatars")
    save_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{user_id}_{int(datetime.now().timestamp())}.jpg"
    file_path = save_dir / filename
    cv2.imwrite(str(file_path), image_np)

    await insert_user_photo_in_db(user_id, str(file_path))

    return {"message": "عکس با موفقیت ذخیره شد", "image_path": str(file_path)}
