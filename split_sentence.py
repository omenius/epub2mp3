# This is a modified version of 'split_sentence' function from TTS.tts.layers.xtts.tokenizer

import textwrap
from TTS.tts.layers.xtts.tokenizer import get_spacy_lang

def split_sentence(text, language):
    limit = 250
    hard_limit = 600
    """Preprocess the input text"""
    text_splits = []
    if len(text) >= limit:
        text_splits.append("")
        nlp = get_spacy_lang(language)
        nlp.add_pipe("sentencizer")
        doc = nlp(text)
        for sentence in doc.sents:
            if len(text_splits[-1]) + len(str(sentence)) <= limit:
                # if the last sentence + the current sentence is less than the limit
                # then add the current sentence to the last sentence
                text_splits[-1] += " " + str(sentence)
                text_splits[-1] = text_splits[-1].lstrip()
            elif len(str(sentence)) > hard_limit:
                print('!!! hard limit broken: \n'+str(sentence))
                # if the current sentence is greater than the hard_limit
                for line in textwrap.wrap(
                    str(sentence),
                    width=hard_limit,
                    drop_whitespace=True,
                    break_on_hyphens=False,
                    tabsize=1,
                ):
                    text_splits.append(str(line))
            else:
                text_splits.append(str(sentence))

        if len(text_splits) > 1:
            if text_splits[0] == "":
                del text_splits[0]
    else:
        text_splits = [text.lstrip()]
    return text_splits
