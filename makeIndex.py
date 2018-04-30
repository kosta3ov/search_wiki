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

tokenizer = RegexpTokenizer(u'(?:[a-zа-я]\.){2,}[a-zа-я]?|\d+(?:[-,.]\d+)*|[a-zа-я]+')

lemmaDict = {}
revertIndex = {}
forwardIndex = {}

class docInfo:
    title = ''
    url = ''
    def __init__(self, title, url):
        self.title = title
        self.url = url

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
    tokens = tokenizer.tokenize(remove_accents(article['text'].lower()))

    docId = int(article['id'])
    title = article['title']
    url = article['url']

    forwardIndex[docId] = docInfo(title, url)

    clearTokens = []
    for i in xrange(len(tokens)):
        token = tokens[i]
        token = token.encode('utf-8')
        if token in lemmaDict:
            token = lemmaDict[token]

        clearTokens.append(token)

        if token not in revertIndex:
            revertIndex[token] = dict()
        if docId not in revertIndex[token]:
            revertIndex[token][docId] = []
        revertIndex[token][docId].append(i)

start_time = time.time()

fileRead = sys.argv[1]

print "--- %s start tokenization" % (time.time() - start_time)
loadLemmaDict()
print "--- %s dict loaded" % (time.time() - start_time)

f = open(fileRead)
for line in f:
    processArticle(line)  

revIndexFile = open(fileRead + '_RevComp', 'wb')
forwardIndexFile = open(fileRead + '_Forw', 'wb')

allKeys = sorted(revertIndex.keys())
for key in allKeys:
    values = sorted(list(revertIndex[key].keys()))
    keyLength = len(key)
    bytearr = struct.pack('I{}s0I'.format(keyLength), keyLength, key)

    dist_v = list(values)
    for i in reversed(xrange(1, len(dist_v))):
        dist_v[i] = dist_v[i] - dist_v[i - 1]
    
    list_for_compression = [len(values)]
    for v in dist_v:
        list_for_compression.append(v)

    for v in values:
        entries = list(revertIndex[key][v])
        for i in reversed(xrange(1, len(entries))):
            entries[i] = entries[i] - entries[i - 1]
        list_for_compression.append(len(entries))
        list_for_compression.extend(entries)

    compressed = vbcode.encode(list_for_compression)
    
    bytearr += struct.pack('I{}s0I'.format(len(compressed)), len(compressed), compressed)

    revIndexFile.write(bytearr)

allDocIds = sorted(forwardIndex.keys())

for docId in allDocIds:
    title = forwardIndex[docId].title.encode('utf-8')
    url = forwardIndex[docId].url.encode('utf-8')
    bytearr = struct.pack('II{}sI{}s0I'.format(len(title), len(url)), docId, len(title), title, len(url), url)
    forwardIndexFile.write(bytearr)

print "--- %s all time" % (time.time() - start_time)

f.close()




 




