import sys
if __name__ != '__main__': sys.exit()

def process_arguments():
    global ARGS, AUTHOR, BOOK_NAME, YEAR, COVER, BOOK
    import argparse as ap
    from epub import extract
    motd = 'Convert epub e-books into mp3 audiobooks.'
    arg_parser = ap.ArgumentParser(description=motd, formatter_class=ap.ArgumentDefaultsHelpFormatter)
    a = arg_parser.add_argument
    i_default = ['contents', 'copyright', 'bibliography']
    a('file', type=str, help='epub file (input)')
    a('-i', '--ignore', default=i_default, nargs='+', type=str.lower, help='ignore given chapter(s)')
    a('-f', '--filter', default='footnote', type=str.lower, help='remove elements with matching class name(s)')
    a('-d', '--dir', default=path.curdir, type=str, help='output directory path')
    a('-s', '--speed', default=1.18, type=float, help='speaker speed: 0.0-2.0')
    a('-n', '--name', default='Royston Min', type=str, help='name of the speaker')
    a('-l', '--lang', default='en', type=str.lower, help='speaker language code')
    a('-b', '--bitrate', default='160k', type=str.lower, help='output bit rate: 8k-160k')
    a('-w', '--wav', action='store_true', help='generate a non compressed wav file')
    a('-v', '--verbose', action='store_true', help='increase output verbosity')
    ARGS = arg_parser.parse_args()

    # Check args
    rates = ['8k','16k','24k','32k','40k','48k','56k','64k','80k','96k','112k','128k','144k','160k']
    langs = ['en','es','fr','de','it','pt','pl','tr','ru','nl','cs','ar','zh-cn','hu','ko','ja','hi']
    if not path.exists(ARGS.file): sys.exit('Epub file not found.')
    if not path.exists(ARGS.dir): sys.exit('Output directory not found.')
    if ARGS.speed<0 or ARGS.speed>2: sys.exit('Speed must be between 0 and 2.')
    if ARGS.bitrate not in rates: sys.exit('Invalid output bit rate. Valid rates are:\n'+str(rates))
    if ARGS.lang not in langs: sys.exit('Invalid language code. Valid languages are:\n'+str(langs))

    try: AUTHOR, BOOK_NAME, YEAR, COVER, BOOK = extract(
            ARGS.file, ignore_chapters=ARGS.ignore, class_filter=ARGS.filter)
    except:
        if ARGS.verbose: raise
        sys.exit('Could not open the given epub file. Use -v flag to see error.')

    if path.exists(path.join(ARGS.dir, BOOK_NAME)):
        sys.exit(f'Name collision. Directory already exists: {BOOK_NAME}')

def load_model():
    global MODEL, GPT_COND_LATENT, SPEAKER_EMBEDDING
    from TTS.tts.configs.xtts_config import XttsConfig
    from TTS.tts.models.xtts import Xtts
    from TTS.utils.manage import ModelManager
    from TTS.utils.generic_utils import get_user_data_dir
    from torch import cuda
    model_name = 'tts_models/multilingual/multi-dataset/xtts_v2'
    ModelManager().download_model(model_name)
    model_path = path.join(get_user_data_dir('tts'), model_name.replace('/', '--'))
    config = XttsConfig()
    config.load_json(path.join(model_path, 'config.json'))
    MODEL = Xtts.init_from_config(config)
    MODEL.load_checkpoint(config, checkpoint_dir=model_path)
    if cuda.is_available(): MODEL.cuda()
    else: print('Cuda GPU not available. Using CPU.')

    # Select a valid speaker
    while ARGS.name not in MODEL.speaker_manager.speakers.keys():
        print(f'Invalid speaker name: {ARGS.name}\n')
        print('Valid names are: ')
        for key in MODEL.speaker_manager.speakers: print(f'{key}, ', end='')
        ARGS.name = input('\n\nEnter a valid name: ')

    GPT_COND_LATENT, SPEAKER_EMBEDDING = MODEL.speaker_manager.speakers[ARGS.name].values()

# Returns a numpy array of silence for a given time
def get_pause(sec):
    return np.zeros(int(sec*24000), dtype=np.float32)

# Returns a numpy array of speech from a given text
def get_speech(text):
    sentences = split_sentence(text, ARGS.lang)
    wavs = []
    for sentence in sentences:
        # import re; sentence = re.sub('([^\x00-\x7F]|\w)(\.|\。|\?)',r'\1 \2\2', sentence)
        try:
            wavs.append(MODEL.inference(
                sentence,
                ARGS.lang,
                GPT_COND_LATENT,
                SPEAKER_EMBEDDING,
                speed=ARGS.speed,
                repetition_penalty=5.0,
                enable_text_splitting = False,
            )['wav'])
        except:
            print('error with sentence: ' + sentence)
            raise

        wavs.append(get_pause(0.6))
    return np.concatenate(wavs)

# === Main function ==========================================================
def main():
    try: mkdir(path.join(ARGS.dir, BOOK_NAME))
    except:
        if ARGS.verbose: raise
        sys.exit(f'Cant create a direcotry in "{ARGS.dir}". Use -v flag to see error.')

    for index, (title, texts) in enumerate(BOOK):
        print(f'Converting chapter {index+1} of {len(BOOK)}: {title}')
        file_path = path.join(ARGS.dir, BOOK_NAME, title)

        # Generate audio
        wavs = []
        wavs.append(get_pause(1))
        for text in texts:
            if text.isspace(): continue
            wavs.append(get_speech(text))
            wavs.append(get_pause(1))
        wavs.append(get_pause(2))
        wav = np.concatenate(wavs)

        # Save to wav
        if ARGS.wav:
            write(file_path+'.wav', 24000, wav)
            continue

        # Convert to mp3 and save
        memoryBuff = BytesIO()
        write(memoryBuff, 24000, wav)
        AudioSegment.from_wav(memoryBuff).export(file_path+'.mp3', format='mp3', bitrate=ARGS.bitrate)
        memoryBuff.close()

        # Write mp3 metadata
        mp3 = eyed3.load(file_path+'.mp3')
        mp3.initTag()
        mp3.tag.track_num = index+1
        mp3.tag.title = title
        mp3.tag.album = BOOK_NAME
        mp3.tag.artist = AUTHOR or 'Unknown'
        mp3.tag.release_date = eyed3.core.Date(YEAR or 1970)
        if COVER:
            mp3.tag.images.set(
                type_=3,
                img_data=COVER.content,
                mime_type=COVER.media_type,
                description='Cover image'
            )
        mp3.tag.save()

    print('Job finished.')

try:
    from os import path, mkdir
    process_arguments()
    print(' ┌┐┌┐╷╷├┐┌┐──────┐\n ├┘├┘└┘└┘┌┘┌┬┐┌┐─┤\n └─╵─────└─╵╵╵├┘─┘\nLoading...')
    import numpy as np
    from split_sentence import split_sentence
    from scipy.io.wavfile import write
    if not ARGS.wav:
        from io import BytesIO
        from pydub import AudioSegment
        import eyed3; eyed3.log.setLevel('ERROR')
    
    load_model()
    main()

except KeyboardInterrupt: sys.exit('Sopped by user.')