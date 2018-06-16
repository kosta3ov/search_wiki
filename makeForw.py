# -*- encoding: utf-8 -*-

from nltk.tokenize import RegexpTokenizer
import unidecode
import unicodedata
import sys
import json
import string
import re
import time
import os
import struct
import vbcode
import math

tokenizer = RegexpTokenizer(u'(?:[a-zа-я]\.){2,}[a-zа-я]?|\d+(?:[-,.]\d+)*|[a-zа-я]+')
lemmaDict = {}
forwardIndex = {}

class docInfo:
    doc_id = 0
    title = ''
    url = ''
    docLen = 0
    text = ''
    def __init__(self, title, url, doc_id, text, docLen):
        self.text = text
        self.doc_id = doc_id
        self.title = title
        self.url = url
        self.docLen = docLen

def loadLemmaDict():
    f1 = open("uniq_words_union", 'r')
    f2 = open("norm_stem", 'r')
    for line in f1:
        line2 = f2.readline()
        lemmaDict[line[:-1]] = line2[:-1]

def remove_accents(input_str):
    nkfd_form = unicodedata.normalize('NFKD', input_str)
    return u"".join([c for c in nkfd_form if not unicodedata.combining(c)])

def processArticle(line):
    article = json.loads(line)

    docId = int(article['id'])
    title = article['title'].encode('utf-8')
    url = article['url'].encode('utf-8')

    text = remove_accents(article['text'].lower())
    tokens = tokenizer.tokenize(text)
    docLen = len(tokens)
    text = " ".join(tokens).encode('utf-8')
    
    bytearr = struct.pack('II{}sI{}sII{}s0I'.format(len(title), len(url), len(text)), docId, len(title), title, len(url), url, docLen, len(text), text)
    forwardIndexFile.write(bytearr)


start = time.time()

fileRead = sys.argv[1]

f = open(fileRead)
forwardIndexFile = open(fileRead + '_Forw', 'wb')

# загрузка словарая лематизации
print "--- %s start tokenization" % (time.time() - start)
loadLemmaDict()
print "--- %s dict loaded" % (time.time() - start)

for line in f:
    processArticle(line)  


allDocIds = sorted(forwardIndex.keys())

print len(allDocIds)   

print "--- %s all time" % (time.time() - start)

f.close()




 




