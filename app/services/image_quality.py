import cv2
import numpy as np
from typing import Tuple, Dict, Optional
from fastapi import UploadFile, HTTPException
import io


class ImageQualityChecker:
    def __init__(self):
        # Load face detection classifier
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

    async def check_image_quality(self, image_file: UploadFile) -> Dict:
        """
        بررسی کیفیت تصویر و اعمال معیارهای مختلف
        """
        try:
            # خواندن تصویر از فایل آپلود شده
            contents = await image_file.read()
            nparr = np.frombuffer(contents, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if image is None:
                raise HTTPException(status_code=400, detail="تصویر نامعتبر است")

            # انجام بررسی‌های مختلف
            blur_score = self._check_blur(image)
            face_detected = self._detect_face(image)
            brightness = self._check_brightness(image)
            resolution = self._check_resolution(image)

            # تنظیم پارامترهای بررسی کیفیت با حساسیت کمتر
            is_blurry = blur_score < 30  # کاهش آستانه تار بودن
            is_brightness_ok = 10 <= brightness <= 90  # افزایش محدوده روشنایی
            is_resolution_ok = resolution >= 300  # کاهش حداقل رزولوشن

            return {
                "is_blurry": is_blurry,
                "blur_score": blur_score,
                "face_detected": face_detected,
                "brightness": brightness,
                "resolution": resolution,
                "is_acceptable": (
                    not is_blurry  # تصویر نباید خیلی تار باشد
                    and face_detected  # باید چهره در تصویر وجود داشته باشد
                    and is_brightness_ok  # روشنایی باید در محدوده مناسب باشد
                    and is_resolution_ok  # حداقل رزولوشن 300 پیکسل
                ),
            }

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"خطا در پردازش تصویر: {str(e)}"
            )

    def _check_blur(self, image: np.ndarray) -> float:
        """
        بررسی تار بودن تصویر با استفاده از لاپلاسین
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # کاهش اندازه کرنل برای حساسیت کمتر
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F, ksize=5).var()
        return laplacian_var

    def _detect_face(self, image: np.ndarray) -> bool:
        """
        تشخیص وجود چهره در تصویر
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # تنظیم پارامترهای تشخیص چهره برای حساسیت کمتر
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.2,  # افزایش برای تشخیص بهتر چهره‌های کوچکتر
            minNeighbors=3,  # کاهش تعداد همسایه‌ها
            minSize=(15, 15),  # کاهش حداقل اندازه چهره
            maxSize=(400, 400),  # افزایش حداکثر اندازه چهره
        )
        return len(faces) > 0

    def _check_brightness(self, image: np.ndarray) -> float:
        """
        بررسی روشنایی تصویر
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # محاسبه میانگین روشنایی با وزن کمتر برای نواحی مرکزی
        height, width = gray.shape
        center_y, center_x = height // 2, width // 2
        center_weight = 1.5  # کاهش وزن مرکز
        weights = np.ones_like(gray, dtype=float)
        y_indices, x_indices = np.ogrid[:height, :width]
        distance = np.sqrt((y_indices - center_y) ** 2 + (x_indices - center_x) ** 2)
        weights = 1.0 + (center_weight - 1.0) * np.exp(
            -distance / (min(height, width) / 3)  # افزایش ناحیه مرکزی
        )
        return float(np.average(gray, weights=weights))

    def _check_resolution(self, image: np.ndarray) -> int:
        """
        بررسی رزولوشن تصویر
        """
        height, width = image.shape[:2]
        return min(width, height)


# ایجاد یک نمونه از کلاس برای استفاده در برنامه
image_quality_checker = ImageQualityChecker()
