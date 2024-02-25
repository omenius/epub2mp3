import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

def flatten(item, result=[]):
    for t in item:
        if isinstance(t, (list, tuple)):
            flatten(t, result)
        else:
            result.append(t)
    return result

uid = 0
def get_chapter_name(doc, chapters):
    name = doc.file_name
    for entry in chapters:
        if entry.href[:len(name)] == name:
            return entry.title
    uid += 1
    return "untitled-"+uid

def get_texts(doc):
    # deletes empty parents with elements
    def recurs_del(e):
        p = e.parent
        e.decompose()
        if p and (p.text.isspace() or not p.text):
            recurs_del(p)

    # removes anything with "footnote" in class name
    def custom_selector(tag):
        if tag.has_attr('class'):
            for c in tag.get('class'):
                if 'footnote' in c.lower():
                    return True
        return False

    soup = BeautifulSoup(doc.get_body_content(), 'html.parser')
    for d in soup.find_all(custom_selector): recurs_del(d)
    texts = soup.get_text().strip().split('\n')
    texts = list(filter(str.strip, texts)) # remove empty and whitespace items # list not needed?
    return texts

def extract(file):
    # returns a tuple like so:
    # (author, book_name, year, cover, [ (chapter_name, [ paragraph1, ... ]), ... ])
    book = epub.read_epub(file, {"ignore_ncx": True})
    docs = book.get_items_of_type(ebooklib.ITEM_DOCUMENT)
    chapters = flatten(book.toc)
    start_href = chapters[0].href.split('#')[0]

    images = book.get_items_of_type(ebooklib.ITEM_IMAGE)
    cover = next((x for x in images if 'cover' in x.file_name), None)

    try: author = book.metadata['http://purl.org/dc/elements/1.1/']['creator'][0][0]
    except: author = None

    try: year = int(book.metadata['http://purl.org/dc/elements/1.1/']['date'][0][0][0:4])
    except: year = None

    I = 0
    STARTED = False
    content = []
    for doc in docs:
        if STARTED and 'titlepage' not in doc.file_name:
            pass
        elif doc.file_name == start_href:
            STARTED = True
        else:
            continue
        
        I+=1
        if I < 24:
            continue

        chapter_name = get_chapter_name(doc, chapters)
        if 'bibliograph' in chapter_name.lower(): continue
        texts = get_texts(doc)
        content.append((chapter_name, texts))

    return (author, book.title, year, cover, content)
