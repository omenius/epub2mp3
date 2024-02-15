from multiprocessing import Process
from multiprocessing import Pipe
import socket
import os
socket_path = '/tmp/say_socket'

# Inferencer subprocess
def brain(brainIn, stopIn, mouthOut):
    # Load TTS model
    print("--- Loading model...")
    from TTS.tts.configs.xtts_config import XttsConfig
    from TTS.tts.models.xtts import Xtts
    config = XttsConfig()
    config.load_json("tts/xtts/config.json")
    model = Xtts.init_from_config(config)
    model.load_checkpoint(config, checkpoint_dir="tts/xtts")
    model.cuda()

    # Compute speaker latents
    print("--- Computing speaker latents...")
    gpt_cond_latent, speaker_embedding = model.get_conditioning_latents(audio_path=["tts/female.wav"])

    # Brain main loop
    while True:
        print("Ready")
        text = brainIn.recv()
        chunks = model.inference_stream(
            text,
            "en",
            gpt_cond_latent,
            speaker_embedding,
            enable_text_splitting = True
        )

        for i, chunk in enumerate(chunks):
            if stopIn.poll():
                stopIn.recv()
                break
            print(f"Received chunk {i} of audio length {chunk.shape[-1]}")
            mouthOut.send(chunk.detach().cpu())

# Audio player subprocess
def mouth(mouthIn, stopIn, pauseIn):
    import sounddevice as sd
    device = "pulse" # default devices are wrong?
    stream = sd.OutputStream(device=device, samplerate=24000, channels=1)
    stream.start()

    # Mouth main loop
    while True:
        if pauseIn.poll():
            pauseIn.recv()
            print("--- Pausing")
            pauseIn.recv()
            print("--- Pause released")

        if stopIn.poll():
            stopIn.recv()
            while mouthIn.poll(): # clear the que
                mouthIn.recv()
            continue
        data = mouthIn.recv()
        stream.write(data)

# Create subprocesses

mouthOut, mouthIn = Pipe()
mouthStopOut, mouthStopIn = Pipe()
mouthPauseOut, mouthPauseIn = Pipe()
mouth_process = Process(target=mouth, args=(mouthIn, mouthStopIn, mouthPauseIn))
mouth_process.start()

brainOut, brainIn = Pipe()
brainStopOut, brainStopIn = Pipe()
brain_process = Process(target=brain, args=(brainIn, brainStopIn, mouthOut))
brain_process.start()

# Remove the socket if exists
try:
    os.unlink(socket_path)
except OSError:
    if os.path.exists(socket_path):
        raise

# Create the Unix socket server for recieving text
server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
server.bind(socket_path)
server.listen(1)

# Main loop
try:
    while True:
        print("--- Listening for incoming connections...")
        connection, client_address = server.accept()
        data = connection.recv(64768)
        connection.close()

        if not data:
            print("!!! NO DATA/EMPTY BINARY ???")
            continue

        msg = data.decode()

        if msg.isspace():
            print("!!! Skipping whitespace msg")
            continue

        if msg == "!Stop":
            print("--- Stop called")
            brainStopOut.send(1)
            mouthStopOut.send(1)
            continue

        if msg == "!Pause":
            mouthPauseOut.send(1)
            continue

        print(msg)
        brainOut.send(msg)
        

except:
    connection.close()
    os.unlink(socket_path)
    mouth_process.kill()
    brain_process.kill()
