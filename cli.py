import argparse
import asyncio
import logging
import math
import os
import cv2
import numpy
import socketio
import sys

from av import VideoFrame
from aiortc.contrib.media import MediaBlackhole, MediaPlayer, MediaRecorder
from aiortc.contrib.signaling import add_signaling_arguments, create_signaling
from aiortc.sdp import candidate_from_sdp, candidate_to_sdp
import json
from aiortc import (
    RTCIceCandidate,
    RTCPeerConnection,
    RTCSessionDescription,
    VideoStreamTrack,
)

sio = socketio.Client()

class FlagVideoStreamTrack(VideoStreamTrack):
    """
    A video track that returns an animated flag.
    """

    def __init__(self):
        super().__init__()  # don't forget this!
        self.counter = 0
        height, width = 480, 640

        # generate flag
        data_bgr = numpy.hstack(
            [
                self._create_rectangle(
                    width=213, height=480, color=(255, 0, 0)
                ),  # blue
                self._create_rectangle(
                    width=214, height=480, color=(255, 255, 255)
                ),  # white
                self._create_rectangle(width=213, height=480, color=(0, 0, 255)),  # red
            ]
        )

        # shrink and center it
        M = numpy.float32([[0.5, 0, width / 4], [0, 0.5, height / 4]])
        data_bgr = cv2.warpAffine(data_bgr, M, (width, height))

        # compute animation
        omega = 2 * math.pi / height
        id_x = numpy.tile(numpy.array(range(width), dtype=numpy.float32), (height, 1))
        id_y = numpy.tile(
            numpy.array(range(height), dtype=numpy.float32), (width, 1)
        ).transpose()

        self.frames = []
        for k in range(30):
            phase = 2 * k * math.pi / 30
            map_x = id_x + 10 * numpy.cos(omega * id_x + phase)
            map_y = id_y + 10 * numpy.sin(omega * id_x + phase)
            self.frames.append(
                VideoFrame.from_ndarray(
                    cv2.remap(data_bgr, map_x, map_y, cv2.INTER_LINEAR), format="bgr24"
                )
            )

    async def recv(self):
        pts, time_base = await self.next_timestamp()

        frame = self.frames[self.counter % 30]
        frame.pts = pts
        frame.time_base = time_base
        self.counter += 1
        return frame

    def _create_rectangle(self, width, height, color):
        data_bgr = numpy.zeros((height, width, 3), numpy.uint8)
        data_bgr[:, :] = color
        return data_bgr

def object_to_string(obj):
    if isinstance(obj, RTCSessionDescription):
        message = {"sdp": obj.sdp, "type": obj.type}
    elif isinstance(obj, RTCIceCandidate):
        message = {
            "candidate": "candidate:" + candidate_to_sdp(obj),
            "id": obj.sdpMid,
            "label": obj.sdpMLineIndex,
            "type": "candidate",
        }
    else:
        message = {"type": "bye"}
    return json.dumps(message, sort_keys=True)


offerSDPReceived = False

async def run(pc, audio_player, video_player, audio_recorder, video_recorder, signaling, role, sio):
    def add_tracks():
        if audio_player and audio_player.audio:
            pc.addTrack( audio_player.audio)

        if video_player and video_player.video:
            pc.addTrack(video_player.video)

    @pc.on("track")
    def on_track(track):
        if track.kind == "audio":
            audio_recorder.addTrack(track)
        if track.kind == "video":
            video_recorder.addTrack(track)

    # connect signaling
    await signaling.connect()

    if role == "offer":
        # send offer
        add_tracks()
        await pc.setLocalDescription(await pc.createOffer())
        await signaling.send(pc.localDescription)
        sio.emit("sendOfferSDP", {'offerSDP': object_to_string(pc.localDescription) + "\n"})

    # consume signaling
    while True:

        obj = await signaling.receive()

        if isinstance(obj, RTCSessionDescription):
            await pc.setRemoteDescription(obj)
            await audio_recorder.start()
            await video_recorder.start()

            if obj.type == "offer":
                # send answer
                add_tracks()
                await pc.setLocalDescription(await pc.createAnswer())
                await signaling.send(pc.localDescription)
                sio.emit("sendAnswerSDP", {'answerSDP': object_to_string(pc.localDescription)})
        elif isinstance(obj, RTCIceCandidate):
            pc.addIceCandidate(obj)
        elif obj is None:
            print("Exiting")
            break

if __name__ == "__main__":
    if os.path.isfile("/home/ilya/Downloads/aiortc-master/examples/videostream-cli/a.wav"):
        os.remove("/home/ilya/Downloads/aiortc-master/examples/videostream-cli/a.wav")
    parser = argparse.ArgumentParser(description="Video stream from the command line")
    parser.add_argument("role", choices=["offer", "answer"])
    parser.add_argument("--play-from", help="Read the media from a file and sent it."),
    parser.add_argument("--record-to", help="Write received media to a file."),
    parser.add_argument("--verbose", "-v", action="count")
    add_signaling_arguments(parser)
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    both_users_in_system = False

    @sio.event
    def getAnswerSDP(sdp):
        pass
        #print(sdp['answerSDP'])
        #for char in (sdp['answerSDP']):
        #    keyboard.press(str(char))
        #keyboard.press(Key.enter)
        #keyboard.release(Key.enter)

    @sio.event
    def getOfferSDP(sdp):
        obj = (sdp['offerSDP'])

    @sio.event
    def connect():
        sio.emit("getClientInfo", {'role': args.role, 'sid': sio.sid})

    @sio.event
    def continueRunningApp(env):
        global both_users_in_system
        both_users_in_system = True

    sio.connect('http://localhost:8080')
    #sio.wait()

    while not both_users_in_system:
        pass

    # create signaling and peer connection
    signaling = create_signaling(args)
    pc = RTCPeerConnection()

    # create media source
    if args.play_from:
        video_player = MediaPlayer("/dev/video0")
        audio_player = MediaPlayer("default", format="pulse")
    else:
        video_player = None
        audio_player = None
    # create media sink
    if args.record_to:
        audio_recorder = MediaRecorder(args.record_to)
        video_recorder = MediaBlackhole()
    else:
        video_recorder = MediaBlackhole()
        audio_recorder = MediaBlackhole()

    # run event loop
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(
            run(
                pc=pc,
                audio_player=audio_player,
                audio_recorder=audio_recorder,
                video_recorder=video_recorder,
                signaling=signaling,
                role=args.role,
                video_player=video_player,
                sio=sio
            )
        )
    except KeyboardInterrupt:
        pass
    finally:
        # cleanup
        if audio_recorder and video_recorder:
            loop.run_until_complete(audio_recorder.stop())
            loop.run_until_complete(video_recorder.stop())
        loop.run_until_complete(signaling.close())
        loop.run_until_complete(pc.close())