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

# lemmaDict = {}
revertIndex = {}
forwardIndex = {}
titleZoneIndex = {}

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

# def loadLemmaDict():
#     f1 = open("uniq_words_union", 'r')
#     f2 = open("norm_stem", 'r')
#     for line in f1:
#         line2 = f2.readline()
#         lemmaDict[line[:-1]] = line2[:-1]

def remove_accents(input_str):
    nkfd_form = unicodedata.normalize('NFKD', input_str)
    return u"".join([c for c in nkfd_form if not unicodedata.combining(c)])

def processArticle(line):
    article = json.loads(line)

    docId = int(article['id'])
    title = article['title']
    url = article['url']
    text = remove_accents(article['text'].lower())

    tokensCount = 0

    tokens = tokenizer.tokenize(text)

    for i in xrange(0, len(tokens)):
        token = tokens[i].encode('utf-8')
        # if token in lemmaDict:
        #     token = lemmaDict[token]

        if token not in revertIndex:
            revertIndex[token] = dict()
        if docId not in revertIndex[token]:
            revertIndex[token][docId] = []
        revertIndex[token][docId].append(i)

    forwardIndex[docId] = docInfo(title, url, docId, " ".join(tokens), len(tokens))

    titleTokens = tokenizer.tokenize(remove_accents(article['title'].lower()))
    titleZoneIndex[docId] = set()
    for i in xrange(len(titleTokens)):
        token = titleTokens[i].encode('utf-8')
        # if token in lemmaDict:
        #     token = lemmaDict[token]
        titleZoneIndex[docId].add(token)


start = time.time()

fileRead = sys.argv[1]

# загрузка словарая лематизации
print "--- %s start tokenization" % (time.time() - start)
# loadLemmaDict()
print "--- %s dict loaded" % (time.time() - start)

f = open(fileRead)
for line in f:
    processArticle(line)  

revIndexFile = open(fileRead + '_RevComp', 'wb')
forwardIndexFile = open(fileRead + '_Forw', 'wb')

allKeys = sorted(revertIndex.keys())
for key in allKeys:
    values = sorted(revertIndex[key].keys())
    keyLength = len(key)

    title_zones = []

    for v in values:
        if key in titleZoneIndex[v]:
            title_zones.append(1)
        else:
            title_zones.append(0)

    dist_v = list(values)
    for i in reversed(xrange(1, len(dist_v))):
        dist_v[i] = dist_v[i] - dist_v[i - 1]

    skipList = range(0, len(values), int(math.sqrt(len(values))))
    
    bytearr = struct.pack('I{}s0III'.format(keyLength), keyLength, key, len(values), len(skipList))

    list_for_compression = title_zones
    list_for_compression.extend(dist_v)
    list_for_compression.extend(skipList)

    compressed = vbcode.encode(list_for_compression)
    bytearr += struct.pack('I{}s0I'.format(len(compressed)), len(compressed), compressed)
    
    for v in values:
        entries = list(revertIndex[key][v])
        for i in reversed(xrange(1, len(entries))):
            entries[i] = entries[i] - entries[i - 1]

        compressed = vbcode.encode(entries)
        bytearr += struct.pack('I{}s0I'.format(len(compressed)), len(compressed), compressed)

    revIndexFile.write(bytearr)

allDocIds = sorted(forwardIndex.keys())

for docId in allDocIds:
    title = forwardIndex[docId].title.encode('utf-8')
    url = forwardIndex[docId].url.encode('utf-8')
    docLen = forwardIndex[docId].docLen
    text = forwardIndex[docId].text.encode('utf-8')

    bytearr = struct.pack('II{}sI{}s0III{}s0I'.format(len(title), len(url), len(text)), docId, len(title), title, len(url), url, docLen, len(text), text)
    forwardIndexFile.write(bytearr)

print "--- %s all time" % (time.time() - start)

f.close()




 




