from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from app.services.image_quality import image_quality_checker
from app.services.auth import get_current_user
from app.models.user import User

router = APIRouter()


@router.post("/check-quality")
async def check_image_quality(
    image: UploadFile = File(...), current_user: User = Depends(get_current_user)
):
    """
    بررسی کیفیت تصویر آپلود شده
    """
    # بررسی نوع فایل
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="فایل باید یک تصویر باشد")

    # بررسی کیفیت تصویر
    quality_result = await image_quality_checker.check_image_quality(image)

    if not quality_result["is_acceptable"]:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "تصویر مورد تایید نیست",
                "reasons": [
                    "تصویر تار است" if quality_result["is_blurry"] else None,
                    (
                        "چهره در تصویر تشخیص داده نشد"
                        if not quality_result["face_detected"]
                        else None
                    ),
                    (
                        "روشنایی تصویر نامناسب است"
                        if not (30 <= quality_result["brightness"] <= 70)
                        else None
                    ),
                    (
                        "رزولوشن تصویر پایین است"
                        if quality_result["resolution"] < 640
                        else None
                    ),
                ],
            },
        )

    return {"message": "تصویر مورد تایید است", "quality_metrics": quality_result}
