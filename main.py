from typing_extensions import Annotated
from fastapi import Depends, FastAPI
from app.config import Settings, get_settings
from app.routers import auth, user, image
from app.db.session import engine, Base, init_db
import os
import logging
from logging.handlers import RotatingFileHandler
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request


import time
from datetime import datetime
from app.db.session import create_tables

app = FastAPI(title="Face Detection API")

# تنظیمات لاگر
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# فرمت لاگ‌ها
formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

# هندلر برای نمایش در کنسول
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# هندلر برای ذخیره در فایل با قابلیت چرخش خودکار
file_handler = RotatingFileHandler(
    "logs/app.log",
    maxBytes=10 * 1024 * 1024,  # 10 مگابایت
    backupCount=5,  # تعداد فایل‌های پشتیبان
    encoding="utf-8",
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# تنظیمات CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # یا دامنه‌های مشخص
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware برای ثبت درخواست‌ها و خطاها
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    # لاگ کردن اطلاعات درخواست
    logger.info(
        f"\n{'='*50}\n"
        f"Request Info:\n"
        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Path: {request.url.path}\n"
        f"Method: {request.method}\n"
        f"Client IP: {request.client.host if request.client else 'Unknown'}\n"
        f"Headers: {dict(request.headers)}\n"
        f"{'='*50}"
    )

    try:
        response = await call_next(request)

        # محاسبه زمان پاسخ
        process_time = time.time() - start_time

        # لاگ کردن اطلاعات پاسخ
        logger.info(
            f"\n{'='*50}\n"
            f"Response Info:\n"
            f"Status Code: {response.status_code}\n"
            f"Process Time: {process_time:.2f}s\n"
            f"{'='*50}"
        )

        return response
    except Exception as e:
        # لاگ کردن خطاها
        logger.error(
            f"\n{'='*50}\n"
            f"Error Info:\n"
            f"Error Type: {type(e).__name__}\n"
            f"Error Message: {str(e)}\n"
            f"{'='*50}"
        )
        raise


@app.get("/")
async def read_root():
    return {"message": "Welcome to Legal Docs App!"}


# ایجاد جداول دیتابیس
@app.on_event("startup")
async def startup_event():
    """Initialize database and tables on startup"""
    try:
        # First check and create database if it doesn't exist
        await init_db()

        # Then create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Database and tables initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise e


# ثبت روترها
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(user.router, prefix="/user", tags=["User"])
app.include_router(image.router, prefix="/image", tags=["Image Processing"])


@app.get("/")
async def root():
    return {"message": "Welcome to Face Detection API"}
