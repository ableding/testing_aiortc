from aiohttp import web
import socketio
import sys

sio = socketio.AsyncServer(async_mode='aiohttp')
app = web.Application()
sio.attach(app)

async def index(request):
    """Serve the client-side application."""
    return web.Response(text="py server test", content_type='text/html')

class Client:
    def __init__(self, role, sid):
        self._role = role
        self._sid = sid

    def getRole(self):
        return self._role

    def getSID(self):
        return self._sid
clients = []

def offerAndAnswerConnected(clients):
    return True if (clients[0].getRole() == 'offer' and clients[1].getRole() == 'answer') or (clients[0].getRole() == 'answer' and clients[1].getRole() == 'offer') else False

def getSIDByRole(clients, role):
    for client in clients:
        if client.getRole() == role:
            return client.getSID()

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
async def sendOfferSDP(sid, sdp):
    await sio.emit("getOfferSDP", {'offerSDP': sdp['offerSDP']}, room=getSIDByRole(clients, "answer"))

@sio.event
async def sendAnswerSDP(sid, sdp):
    print("yeeeaaaah")
    #await sio.emit("getAnswerSDP", {'answerSDP': sdp['answerSDP']}, room=getSIDByRole(clients, "offer"))

@sio.event
async def connect(sid, environ):
    pass
    #print("connect ", sid)
    #clients.append(sid)
    #await sio.emit('get_connected_clients', {'clients': clients})

@sio.event
def disconnect(sid):
    print('disconnect ', sid)

app.router.add_get('/', index)
web.run_app(app)