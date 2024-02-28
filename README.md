# epub2mp3
```
 ┌┐┌┐╷╷├┐┌┐──────┐
 ├┘├┘└┘└┘┌┘┌┬┐┌┐╶┤
 └─╵─────└─╵╵╵├┘─┘
```

## do the needful
```bash
python -m venv venv
source venv/bin/activate
pip install TTS sounddevice eyed3 EbookLib beautifulsoup4 pydub
```

## epub2mp3.py
Convert epub e-books into mp3 audiobooks.
For example:```python epub2mp3.py /mnt/warez/isaif.epub -d ~/Audiobooks```
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

## stream/socket_service.py
Listens to /tmp/say_socket for text and streams it as speech to sound device almost instantly. Works with UNIX only.

This is not a part of epub2mp3 program, but a standalone service. Send text to socket using ```python send_socket.py "hello"``` or preferably with something like socat or netcat. You can for example makea a shortcut that pipes your text selection to the speech service. Using i3 wm, you could do it like this:
```bash
bindsym $mod+y exec xsel | socat -u - UNIX-CONNECT:/tmp/say_socket
bindsym $mod+Shift+y exec echo -n "!Stop" | socat -u - UNIX-CONNECT:/tmp/say_socket
bindsym $mod+u exec echo -n "!Pause" | socat -u - UNIX-CONNECT:/tmp/say_socket
```
