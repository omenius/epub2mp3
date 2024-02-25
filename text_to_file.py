speaker_name = 'Royston Min'
language='en'
speed = 1.18 # 0-2

from sys import argv
from os import path, mkdir
from epub import extract

if not argv[1] or not path.exists(argv[1]):
    print('Epub not found.')
    exit()

AUTHOR, NAME, YEAR, COVER, BOOK = extract(argv[1])

try: mkdir(NAME)
except:
    print("Cant create a directory. Maybe it already exists?")
    exit()

print('Loading...')
from split_sentence import split_sentence
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts
from TTS.utils.manage import ModelManager
from TTS.utils.generic_utils import get_user_data_dir
from scipy.io.wavfile import write
from pydub import AudioSegment
from io import BytesIO
from torch import cuda
import numpy as np
import eyed3; eyed3.log.setLevel("ERROR")

model_name = 'tts_models/multilingual/multi-dataset/xtts_v2'
ModelManager().download_model(model_name)
model_path = path.join(get_user_data_dir('tts'), model_name.replace('/', '--'))
config = XttsConfig()
config.load_json(path.join(model_path, 'config.json'))
model = Xtts.init_from_config(config)
model.load_checkpoint(config, checkpoint_dir=model_path)
if cuda.is_available(): model.cuda()

gpt_cond_latent, speaker_embedding = model.speaker_manager.speakers[speaker_name].values()

def get_pause(sec):
    pause = int(sec*24000)
    return np.zeros(pause, dtype=np.float32)

def get_wav(text):
    sentences = split_sentence(text, language)
    wavs = []
    for sentence in sentences:
        # import re; sentence = re.sub("([^\x00-\x7F]|\w)(\.|\。|\?)",r"\1 \2\2", sentence)
        try:
            wavs.append(model.inference(
                sentence,
                language,
                gpt_cond_latent,
                speaker_embedding,
                speed=speed,
                repetition_penalty=5.0,
                temperature=0.75,
                enable_text_splitting = False,
            )['wav'])
        except:
            print("error:")
            print(sentence)

        wavs.append(get_pause(0.6))
    return np.concatenate(wavs)

# == MAIN ================================
print('Job started')

for index, (title, texts) in enumerate(BOOK):
    wavs = []
    wavs.append(get_pause(1))
    for text in texts:
        if text.isspace(): continue
        wavs.append(get_wav(text))
        wavs.append(get_pause(1))
    wavs.append(get_pause(2))

    wav = np.concatenate(wavs)
    memoryBuff = BytesIO()
    write(memoryBuff, 24000, wav)
    mp3_path = path.join(NAME, title)+'.mp3'
    AudioSegment.from_wav(memoryBuff).export(mp3_path, format='mp3', bitrate='192k')
    memoryBuff.close()

    mp3 = eyed3.load(mp3_path)
    mp3.initTag()
    mp3.tag.track_num = index+1
    mp3.tag.title = title
    mp3.tag.album = NAME
    mp3.tag.artist = AUTHOR or 'Unknown'
    date = YEAR and eyed3.core.Date(YEAR) or eyed3.core.Date(1970)
    mp3.tag.release_date = date
    # mp3.tag.recording_date = eyed3.core.Date(year)
    if COVER:
        mp3.tag.images.set(
            type_=3,
            img_data=COVER.content,
            mime_type=COVER.media_type,
            description='Cover image'
        )
    mp3.tag.save()

    print('Done chapter: '+title)
