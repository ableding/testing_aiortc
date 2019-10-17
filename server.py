from aiohttp import web
import socketio

sio = socketio.AsyncServer()
app = web.Application()
sio.attach(app)

async def index(request):
    """Serve the client-side application."""
    return web.Response(text="py server test", content_type='text/html')

class Client:
    def __init__(self, name, sid):
        self.name = name
        self.sid = sid

clients = []

@sio.event
async def connect(sid, environ):
    print("connect ", sid)
    clients.append(sid)
    await sio.emit('connected_clients', {'clients': clients})

@sio.event
async def message(sid, data):
    print("message ", data)
    #await sio.emit('reply', room=sid)

@sio.event
def disconnect(sid):
    print('disconnect ', sid)

app.router.add_get('/', index)

if __name__ == '__main__':
    web.run_app(app)