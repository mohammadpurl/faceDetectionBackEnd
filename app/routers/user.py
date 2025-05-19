from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pathlib import Path
import cv2
import numpy as np
from datetime import datetime, UTC
from app.services.auth import get_current_user
from app.models.user import User
from app.services.user_service import insert_user_photo_in_db

router = APIRouter()


def is_blurry(image_np, threshold=100):
    gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    return laplacian_var < threshold


def is_frontal_face(image_np):
    # این تابع باید با استفاده از مدل‌های تشخیص چهره (مثلاً dlib یا mediapipe) پیاده‌سازی شود
    # به طور ساده: اگر یک چهره پیدا شد و زاویه آن مناسب بود True برگرداند
    return True  # پیاده‌سازی دقیق نیاز به کد بیشتر دارد


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
    filename = f"{user_id}_{int(datetime.now(UTC).timestamp())}.jpg"
    file_path = save_dir / filename
    cv2.imwrite(str(file_path), image_np)

    await insert_user_photo_in_db(user_id, str(file_path))

    return {"message": "عکس با موفقیت ذخیره شد", "image_path": str(file_path)}
