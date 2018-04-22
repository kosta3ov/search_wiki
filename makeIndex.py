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

count = 0
lengthOfTokens = 0
tokenizer = RegexpTokenizer(u'(?:[a-zа-я]\.){2,}[a-zа-я]?|\d+(?:[-,.]\d+)*|[a-zа-я]+')

lemmaDict = {}
revertIndex = {}

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

        if len(revertIndex[token][docId]) == 0:
            revertIndex[token][docId].append(i)
        else:
            revertIndex[token][docId].append(i - revertIndex[token][docId][-1])

start_time = time.time()
fileRead = sys.argv[1]

print "--- %s start tokenization" % (time.time() - start_time)
loadLemmaDict()
print "--- %s dict loaded" % (time.time() - start_time)

f = open(fileRead)
for line in f:
    processArticle(line)  

revIndexFile = open(fileRead + '_revert', 'wb')

allKeys = sorted(revertIndex.keys())
for key in allKeys:
    values = sorted(list(revertIndex[key].keys()))
    keyLength = len(key)
    bytearr = struct.pack('I{}sI'.format(keyLength), keyLength, key, len(values))
    for v in values:
        entries = revertIndex[key][v]
        bytearr += struct.pack('II{}I'.format(len(entries)), v, len(entries), *entries)
    revIndexFile.write(bytearr)

print "--- %s all time" % (time.time() - start_time)

f.close()




 




