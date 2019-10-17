import socketio

sio = socketio.Client()

@sio.event
def connect():
    print('connection established')


@sio.event
def my_message(data):
    sio.emit('message', {'data': data})

@sio.event
def connected_clients(data):
    print("got new cli")


@sio.event
def disconnect():
    print('disconnected from server')

sio.connect('http://localhost:8080')
my_message("hello")
#sio.wait()
