# Modules are heavy, so we don't do imports unless arguments are good

def process_arguments():
    motd = 'Convert epub e-books into mp3 audiobooks.'
    i_default = ['contents', 'copyright', 'bibliography']
    arg_parser = ap.ArgumentParser(description=motd, formatter_class=ap.ArgumentDefaultsHelpFormatter)
    a = arg_parser.add_argument
    a('file',                               help='epub file (input)',       type=str)
    a('-d','--dir',     default=path.curdir, help='output directory path',  type=str)
    a('-n','--name',    default='Royston Min', help='name of the speaker',  type=str)
    a('-l','--lang',    default='en',       help='speaker language code',   type=str.lower)
    a('-b','--bitrate', default='160k',     help='output bit rate: 8k-160k',type=str.lower)
    a('-s','--speed',   default=1.19,       help='speaker speed: 0.0-2.0',  type=float)
    a('-i','--ignore',  default=i_default,  help='ignore given chapter(s)', type=str.lower, nargs='+')
    a('-f','--filter',  default='footnote', help='remove elements with matching class name', type=str.lower)
    a('-S','--start',   default=None,       help='Chapter to start from',   type=str.lower)
    a('-E','--end',     default=None,       help='End to this chapter',       type=str.lower)
    a('-r','--rm-links',action='store_true', help='remove html <a> elements')
    a('-w','--wav',     action='store_true', help='generate a non compressed wav file')
    a('-v','--verbose', action='store_true', help='increase output verbosity')
    args = arg_parser.parse_args()

    # Check args
    rates = ['8k','16k','24k','32k','40k','48k','56k','64k','80k','96k','112k','128k','144k','160k']
    langs = ['en','es','fr','de','it','pt','pl','tr','ru','nl','cs','ar','zh-cn','hu','ko','ja','hi']
    if not path.exists(args.file):
        sys.exit('Epub file not found.')
    if not path.exists(args.dir):
        sys.exit('Output directory not found.')
    if args.speed<0 or args.speed>2:
        sys.exit('Speed must be between 0 and 2.')
    if args.bitrate not in rates:
        sys.exit('Invalid output bit rate. Valid rates are:\n'+str(rates))
    if args.lang not in langs:
        sys.exit('Invalid language code. Valid languages are:\n'+str(langs))
    return args

def load_book():
    try: book = extract(ARGS.file, ARGS.ignore, ARGS.filter, ARGS.start, ARGS.end, ARGS.rm_links)
    except:
        if ARGS.verbose: raise
        sys.exit('Could not open the given epub file. Use -v flag to see the error.')
    return book

import sys
from os import path, mkdir
import argparse as ap
ARGS = process_arguments()
from epub import extract
AUTHOR, BOOK_NAME, YEAR, COVER, BOOK = load_book()
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts
from TTS.utils.manage import ModelManager
from TTS.utils.generic_utils import get_user_data_dir
from torch import cuda
import numpy as np
from scipy.io.wavfile import write
from split_sentence import split_sentence
if not ARGS.wav:
    from io import BytesIO
    from pydub import AudioSegment
    import eyed3; eyed3.log.setLevel('ERROR')

# load XTTS text-to-speech model and speaker latents
def load_model():
    global MODEL

    model_name = 'tts_models/multilingual/multi-dataset/xtts_v2'
    ModelManager().download_model(model_name)
    model_path = path.join(get_user_data_dir('tts'), model_name.replace('/','--'))
    config = XttsConfig()
    config.load_json(path.join(model_path, 'config.json'))
    model = Xtts.init_from_config(config)
    model.load_checkpoint(config, checkpoint_dir=model_path)
    if cuda.is_available(): model.cuda()
    else: print('Cuda GPU not available. Using CPU.')

    # Select a valid speaker
    while ARGS.name not in model.speaker_manager.speakers.keys():
        print(f'Invalid speaker name: {ARGS.name}\n')
        print('Valid names are: ')
        for key in model.speaker_manager.speakers: print(f'{key}, ', end='')
        ARGS.name = input('\n\nEnter a valid name: ')
    latent, speaker = model.speaker_manager.speakers[ARGS.name].values()

    MODEL = {
        'model': model,
        'gpt_cond_latent': latent,
        'speaker_embedding': speaker
    }

# Add metadata to mp3 file
def tag_mp3(file_path, track_num, title):
    mp3 = eyed3.load(file_path)
    mp3.initTag()
    mp3.tag.track_num = track_num
    mp3.tag.title = title
    mp3.tag.album = BOOK_NAME
    mp3.tag.artist = AUTHOR or 'Unknown'
    mp3.tag.release_date = eyed3.core.Date(YEAR or 1970)
    if COVER:
        mp3.tag.images.set(
            type_ = 3,
            img_data = COVER.content,
            mime_type = COVER.media_type,
            description = 'Cover image'
        )
    mp3.tag.save()

# Returns a numpy array of silence for a given time
def get_pause(sec):
    return np.zeros(int(sec*24000), dtype=np.float32)

# Returns a numpy array of speech from a given text
def get_speech(text):
    sentences = split_sentence(text, ARGS.lang)
    wavs = []
    if ARGS.verbose: print('\033[32m###\033[m','\033[32m && \033[m'.join(sentences))

    for sentence in sentences:
        try:
            speech = MODEL['model'].inference(
                sentence,
                ARGS.lang,
                MODEL['gpt_cond_latent'],
                MODEL['speaker_embedding'],
                speed = ARGS.speed,
                repetition_penalty = 5.0,
                enable_text_splitting = False,
            )
        except KeyboardInterrupt: raise
        except: print('error with sentence:\n', sentence); raise

        wavs.append(speech['wav'])
        wavs.append(get_pause(0.5)) # pause after sentence

    wavs.append(get_pause(0.4)) # pause after paragraph
    return np.concatenate(wavs)

# === Main function ==============================================
def main():
    print(' ┌┐┌┐╷╷├┐┌┐──────┐\n ├┘├┘└┘└┘┌┘┌┬┐┌┐─┤\n └─╵─────└─╵╵╵├┘─┘\nLoading...')
    load_model()

    if not path.exists(path.join(ARGS.dir, BOOK_NAME)):
        try: mkdir(path.join(ARGS.dir, BOOK_NAME))
        except:
            if ARGS.verbose: raise
            sys.exit(f'Cant create a direcotry in "{ARGS.dir}". Use -v flag to see the error.')
    else: print('Output directory already exists. Continuing a previous job.')

    for index, (title, texts) in enumerate(BOOK):
        file_path = path.join(ARGS.dir, BOOK_NAME, title) + (ARGS.wav and '.wav' or '.mp3')

        # Skip chapter if file exists
        if path.exists(file_path): continue

        # Generate audio
        print(f'Converting chapter {index+1} of {len(BOOK)}: {title}')
        wavs = []
        wavs.append(get_pause(1)) # pause before chapter
        for t in texts: wavs.append(get_speech(t))
        wavs.append(get_pause(1)) # pause after chapter
        wav = np.concatenate(wavs)

        # Save to wav
        if ARGS.wav:
            write(file_path, 24000, wav)
            continue

        # Convert to mp3 and save
        memoryBuff = BytesIO()
        write(memoryBuff, 24000, wav)
        AudioSegment.from_wav(memoryBuff).export(
            file_path,
            format = 'mp3',
            bitrate = ARGS.bitrate
        )
        memoryBuff.close()
        tag_mp3(file_path, index+1, title)

    print('Job finished.')

try: main()
except KeyboardInterrupt: sys.exit('Sopped by user.')
