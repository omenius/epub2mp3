from multiprocessing import Process, Pipe
import socket
import os
socket_path = '/tmp/say_socket'
language = 'en'
speaker_name = 'Royston Min'
speed = 1.17 # 1.0-2.0

# Inferencer subprocess
def brain(brainPipe, stopPipe, mouthPipe):
    # Load TTS model
    print('--- Loading model...')
    import re
    import pysbd
    from TTS.tts.configs.xtts_config import XttsConfig
    from TTS.tts.models.xtts import Xtts
    from TTS.utils.manage import ModelManager
    from TTS.utils.generic_utils import get_user_data_dir
    model_name = 'tts_models/multilingual/multi-dataset/xtts_v2'
    ModelManager().download_model(model_name)
    model_path = os.path.join(get_user_data_dir('tts'), model_name.replace('/', '--'))
    config = XttsConfig()
    config.load_json(os.path.join(model_path, 'config.json'))
    model = Xtts.init_from_config(config)
    model.load_checkpoint(config, checkpoint_dir=model_path)
    model.cuda()

    # Load or compute speaker latents
    gpt_cond_latent, speaker_embedding = model.speaker_manager.speakers[speaker_name].values()
    # gpt_cond_latent, speaker_embedding = model.get_conditioning_latents(audio_path=['female.wav'])

    segmenter = pysbd.Segmenter(language=language, clean=True)
    class Stop(Exception): pass

    # Brain main loop
    while True:
        print('Ready')
        text = brainPipe[1].recv()
        sentences = segmenter.segment(text)

        try:
            for sentence in sentences:
                # this is stupid but it works. Source: coqui/xtts/blob/main/app.py
                # sentence = re.sub("([^\x00-\x7F]|\w)(\.|\。|\?)",r"\1 \2\2", sentence)

                chunks = model.inference_stream(
                    sentence,
                    language,
                    gpt_cond_latent,
                    speaker_embedding,
                    enable_text_splitting = False,
                    speed = speed,
                    overlap_wav_len = 1024,
                    stream_chunk_size=20,
                    repetition_penalty=5.0,
                    temperature=0.75
                )

                for i, chunk in enumerate(chunks):
                    print(f'Received chunk {i} of audio length {chunk.shape[-1]}')
                    data = chunk.detach().cpu()

                    if stopPipe[1].poll():
                        stopPipe[1].recv()
                        raise Stop

                    mouthPipe[0].send(data)

                mouthPipe[0].send('!breath') # pause between sentences

        except Stop:
            continue

# Audio player subprocess
def mouth(mouthPipe, pausePipe):
    import sounddevice as sd
    from time import sleep
    device = 'pulse' # default devices are wrong?
    stream = sd.OutputStream(device=device, samplerate=24000, channels=1)
    stream.start()

    # Mouth main loop
    while True:
        if pausePipe[1].poll():
            pausePipe[1].recv()
            print('--- Pausing')
            pausePipe[1].recv()
            print('--- Pause released')

        data = mouthPipe[1].recv()

        if data == '!breath':
            sleep(0.6)
            continue

        stream.write(data)

# Create subprocesses
mouthPipe = Pipe()
pausePipe = Pipe()
mouth_process = Process(target=mouth, args=(mouthPipe, pausePipe))
mouth_process.start()

brainPipe = Pipe()
stopPipe = Pipe()
brain_process = Process(target=brain, args=(brainPipe, stopPipe, mouthPipe))
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
        print('--- Listening for incoming connections...')
        connection, client_address = server.accept()
        data = connection.recv(64768)
        connection.close()

        if not data:
            print('!!! NO DATA/EMPTY BINARY ???')
            continue

        msg = data.decode()

        if msg.isspace():
            continue

        if msg == '!Stop':
            print('--- Stop called')
            if not stopPipe[1].poll():
                stopPipe[0].send(1)
                while mouthPipe[1].poll():
                    mouthPipe[1].recv()
            continue

        if msg == '!Pause':
            pausePipe[0].send(1)
            continue

        print(msg)

        # clear stop signals if exists
        while stopPipe[1].poll():
            stopPipe[1].recv()

        brainPipe[0].send(msg)
        

except:
    connection.close()
    os.unlink(socket_path)
    mouth_process.kill()
    brain_process.kill()
