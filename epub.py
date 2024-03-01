import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

def flatten(item, result=[]):
    for t in item:
        if isinstance(t, (list, tuple)): flatten(t, result)
        else: result.append(t)
    return result

UID = 0
def get_chapter_name(doc, chapters):
    name = doc.file_name
    for entry in chapters:
        if entry.href[:len(name)] == name:
            return entry.title
    global UID
    UID += 1
    return "untitled-"+str(UID)

def get_texts(doc, class_filter=[], remove_links=False):
    # deletes empty parents with elements
    def recurs_del(e):
        p = e.parent
        e.decompose()
        if p and (p.text.isspace() or not p.text):
            recurs_del(p)

    # removes anything with remove[n] in class name
    def custom_selector(tag):
        if remove_links and tag.name == 'a': return True
        if tag.has_attr('class'):
            for c in tag.get('class'):
                for f in class_filter.split(' '):
                    if f in c.lower():
                        return True
        return False

    body = doc.get_body_content()
    body = body.replace(b'</p>', b'</p>\n')
    soup = BeautifulSoup(body, 'html.parser')
    for d in soup.find_all(custom_selector): recurs_del(d) # remove custom_selector items
    texts = soup.get_text().strip()
    texts = texts.split('\n')
    texts = list(filter(str.strip, texts)) # remove empty and whitespace items
    return texts

def extract(file, ignore_chapters=[], class_filter=[], start_chapter=None, end_chapter=None, remove_links=False):
    # returns a tuple like so:
    # (author, book_name, year, cover, [ (chapter_name, [ paragraph1, ... ]), ... ])
    book = epub.read_epub(file, {"ignore_ncx": True})
    docs = book.get_items_of_type(ebooklib.ITEM_DOCUMENT)
    chapters = flatten(book.toc)
    start_chapter = start_chapter or chapters[0].title

    images = book.get_items_of_type(ebooklib.ITEM_IMAGE)
    cover = next((x for x in images if 'cover' in x.file_name), None)

    try: author = book.get_metadata('DC', 'creator')[0][0]
    except: author = None

    try: year = int(book.get_metadata('DC', 'date')[0][0][:4])
    except: year = None

    try: title = book.get_metadata('DC', 'title')[0][0]
    except: title = book.title

    started = False
    content = []
    for doc in docs:
        chapter_name = get_chapter_name(doc, chapters)

        if started and 'titlepage' not in doc.file_name:
            pass
        elif chapter_name.lower() == start_chapter.lower():
            started = True
        else:
            continue
        
        if chapter_name.lower() in ignore_chapters: continue

        texts = get_texts(doc, class_filter=class_filter, remove_links=remove_links)
        if not texts: continue

        content.append((chapter_name, texts))

        if chapter_name == end_chapter: break

    global UID
    UID = 0
    return (author, title, year, cover, content)
