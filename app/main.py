from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api.recipes import router as recipes_router

app = FastAPI()

# Mount per .well-known (per generare i deep link Android)
app.mount(
    "/.well-known",
    StaticFiles(directory="app/static/.well-known"),
    name="well_known"
)

# Include gli altri router
app.include_router(recipes_router)

@app.get("/")
async def root():
    return {"data": "Hi!"}

@app.get("/list")
async def get_list(listId: str):
    return {"message": f"Received listId: {listId}"}

@app.get("/recipe")
async def get_recipe(recipeId: str):
    return {"message": f"Received recipeId: {recipeId}"}

