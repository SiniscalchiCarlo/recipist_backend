from fastapi import FastAPI
from fastapi.responses import HTMLResponse
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
    return {"data": "Hi v1!"}

@app.get("/list", response_class=HTMLResponse)
async def get_list(listId: str, token: str):
    return f"""
    <!DOCTYPE html>
    <html>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Apertura lista</title>
      </head>
      <body style="font-family: system-ui; padding: 20px; text-align: center;">
        <h2>🛒 Apertura lista della spesa...</h2>
        <p>Se l'app non si apre automaticamente, <a href="https://backend-recipist.fly.dev/list?listId={listId}&token={token}">clicca qui</a>.</p>
        <script>
          window.location.href =
            "intent://backend-recipist.fly.dev/list?listId={listId}&token={token}"
            + "#Intent;scheme=https;package=com.smartShoppingList.app;end";
        </script>
      </body>
    </html>
    """

@app.get("/recipe", response_class=HTMLResponse)
async def open_recipe(recipeId: str, token: str):
    return f"""
    <!DOCTYPE html>
    <html>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Apertura ricetta</title>
      </head>
      <body style="font-family: system-ui; padding: 20px; text-align: center;">
        <h2>🍳 Apertura ricetta...</h2>
        <p>Se l'app non si apre automaticamente, <a href="https://backend-recipist.fly.dev/recipe?recipeId={recipeId}&token={token}">clicca qui</a>.</p>
        <script>
          window.location.href =
            "intent://backend-recipist.fly.dev/recipe?recipeId={recipeId}&token={token}"
            + "#Intent;scheme=https;package=com.smartShoppingList.app;end";
        </script>
      </body>
    </html>
    """
