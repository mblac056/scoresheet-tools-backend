from mangum import Mangum
from app import app

asgi_handler = Mangum(app)

def handler(event, context):
    return asgi_handler(event, context)
