from fastapi import APIRouter, UploadFile, File
from pathlib import Path
from app.services.backblaze import BackblazeStorageService
import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recipes", tags=["recipes"])
service = BackblazeStorageService(enable_logging=True)

@router.post("/{recipe_id}/image")
async def upload_recipe_image(recipe_id: str, file: UploadFile = File(...)):
    print("📥 Upload recipe image request received")
    print(f"Recipe ID: {recipe_id}")
    print(f"Filename: {file.filename}")
    print(f"Content type: {file.content_type}")

    temp_path = Path(f"/tmp/{file.filename}")
    temp_path.write_bytes(await file.read())

    print(f"📦 Saved temp file to: {temp_path}")

    url = service.upload_file(temp_path, f"recipe_cover/{recipe_id}")
    print(f"✅ Uploaded to Backblaze: {url}")
    return {"url": url}

@router.post("/{recipe_id}/steps/image")
async def upload_recipe_step(recipe_id: str, file: UploadFile = File(...)):
    temp_path = Path(f"/tmp/{file.filename}")
    temp_path.write_bytes(await file.read())
    url = service.upload_file(temp_path, f"recipe_steps/{recipe_id}")
    return {"url": url}

@router.delete("/{recipe_id}/assets")
async def delete_recipe_assets(recipe_id: str):
    service.delete_prefix(f"recipe_cover/{recipe_id}")
    service.delete_prefix(f"recipe_steps/{recipe_id}")
    return {"status": "deleted"}

@router.delete("/{recipe_id}/image")
async def delete_recipe_cover(recipe_id: str):
    prefix = f"recipe_cover/{recipe_id}"
    service.delete_prefix(prefix)
    return {"status": "cover_deleted"}

@router.delete("/{recipe_id}/steps")
async def delete_recipe_step_images(recipe_id: str):
    prefix = f"recipe_steps/{recipe_id}"
    service.delete_prefix(prefix)
    return {"status": "steps_deleted"}

@router.delete("/{recipe_id}/steps/{filename}")
async def delete_single_step_image(recipe_id: str, filename: str):
    auth = service.authorize()

    prefix = service._encode(f"recipe_steps/{recipe_id}/{filename}")
    files = service.list_files(auth, prefix)

    for f in files:
        service.delete_file(auth, f)

    return {"status": "step_image_deleted", "file": filename}

@router.put("/{recipe_id}/image")
async def update_recipe_cover(recipe_id: str, file: UploadFile = File(...)):
    # elimina vecchia
    service.delete_prefix(f"recipe_cover/{recipe_id}")

    # salva nuova
    temp_path = Path(f"/tmp/{file.filename}")
    temp_path.write_bytes(await file.read())

    url = service.upload_file(temp_path, f"recipe_cover/{recipe_id}")

    return {"status": "cover_updated", "url": url}

@router.put("/{recipe_id}/steps/{step_id}/image")
async def update_step_image(recipe_id: str, step_id: str, file: UploadFile = File(...)):
    # elimina vecchie immagini dello step
    prefix = f"recipe_steps/{recipe_id}/{step_id}"
    service.delete_prefix(prefix)

    # salva nuova
    temp_path = Path(f"/tmp/{file.filename}")
    temp_path.write_bytes(await file.read())

    url = service.upload_file(temp_path, prefix)

    return {"status": "step_updated", "url": url}

@router.delete("/{recipe_id}")
async def delete_entire_recipe(recipe_id: str):
    service.delete_prefix(f"recipe_cover/{recipe_id}")
    service.delete_prefix(f"recipe_steps/{recipe_id}")
    return {"status": "recipe_deleted"}

