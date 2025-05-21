from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, image
from app.db.session import engine
from app.models import user

# Create database tables
user.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Face Detection API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(image.router, prefix="/image", tags=["Image Processing"])


@app.get("/")
async def root():
    return {"message": "Welcome to Face Detection API"}
