# epub2mp3

## do the needful
```bash
python -m venv venv
source venv/bin/activate
pip install TTS sounddevice eyed3 EbookLib beautifulsoup4 pydub
```
## socket_stream.py
Works with UNIX only. Listens to /tmp/say_socket and streams audio to sound device almost instantly.

Send text to socket using ```python send_socket.py "hello"``` or preferably with something like socat or netcat.

## epub2mp3.py
Convert epub e-books into mp3 audiobooks.
```
usage: epub2mp3.py [-h] [-i IGNORE [IGNORE ...]] [-f FILTER] [-d DIR] [-s SPEED] [-n NAME]
                   [-l LANG] [-b BITRATE] [-w] [-v]
                   file

Convert epub e-books into mp3 audiobooks.

positional arguments:
  file                  epub file (input)

options:
  -h, --help            show this help message and exit
  -i IGNORE [IGNORE ...], --ignore IGNORE [IGNORE ...]
                        ignore given chapter(s) (default: ['contents', 'copyright',
                        'bibliography'])
  -f FILTER, --filter FILTER
                        remove elements with matching class name(s) (default: footnote)
  -d DIR, --dir DIR     output directory path (default: .)
  -s SPEED, --speed SPEED
                        speaker speed: 0.0-2.0 (default: 1.18)
  -n NAME, --name NAME  name of the speaker (default: Royston Min)
  -l LANG, --lang LANG  speaker language code (default: en)
  -b BITRATE, --bitrate BITRATE
                        output bit rate: 8k-160k (default: 160k)
  -w, --wav             generate a non compressed wav file (default: False)
  -v, --verbose         increase output verbosity (default: False)
```
