from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from ..hub import Hub

app = FastAPI()
templates = Jinja2Templates(directory="templates")

def run_dashboard(hub: Hub, host: str = "0.0.0.0", port: int = 8080):
    """Run the web dashboard."""
    @app.get("/")
    async def root(request: Request):
        devices = hub.list_devices()
        return templates.TemplateResponse("index.html", {"request": request, "devices": devices})

    # Add more routes as needed, e.g., /devices/{id}, /control
    import uvicorn
    uvicorn.run(app, host=host, port=port)