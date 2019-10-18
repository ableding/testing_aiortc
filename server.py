from aiohttp import web
import socketio

sio = socketio.AsyncServer(async_mode='aiohttp')
app = web.Application()
sio.attach(app)

async def index(request):
    """Serve the client-side application."""
    return web.Response(text="py server test", content_type='text/html')

class Client:
    def __init__(self, role, sid):
        self.role = role
        self.sid = sid

clients = []

def offerAndAnswerConnected(clients):
    return True if (clients[0].role == 'offer' and clients[1].role == 'answer') or (clients[0].role == 'answer' and clients[1].role == 'offer') else False

@sio.event
async def connect(sid, environ):
    pass


@sio.event
async def getClientInfo(data, env):
    print(env)
    clients.append(Client(env['role'], env['sid']))

    if len(clients) == 2:
        if offerAndAnswerConnected(clients):
            await sio.emit("continueRunningApp")
        else:
            print("no")

@sio.event
def f():
    print("yeeeeeeeeeeeeeeeeeeeeeeah")

@sio.event
async def sendOfferSDP(data, env):
    print(env['offerSDP'])

@sio.event
def disconnect(sid):
    print('disconnect ', sid)

app.router.add_get('/', index)
web.run_app(app)