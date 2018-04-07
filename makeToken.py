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
    global count
    global lengthOfTokens
    
    article = json.loads(line)
    tokens = tokenizer.tokenize(remove_accents(article['text'].lower()))

    clearTokens = set()
    
    for i in tokens:
        i = i.encode('utf-8')
        if i in lemmaDict:
            i = lemmaDict[i]

        lengthOfTokens += len(i)
        clearTokens.add(i)

        if i not in revertIndex:
            revertIndex[i] = set()
        revertIndex[i].add(int(article['id']))

    count += len(tokens)
    doc = docInfo(article['title'].encode('utf-8'),
                 article['url'].encode('utf-8'))
    forwardIndex[int(article['id'])] = doc

start_time = time.time()
fileRead = sys.argv[1]

print "--- %s start tokenization" % (time.time() - start_time)
loadLemmaDict()
print "--- %s dict loaded" % (time.time() - start_time)

f = open(fileRead)
for line in f:
    processArticle(line)

print "count = " + str(count)
print "avg_len = " + str(lengthOfTokens / float(count))    

revIndexFile = open(fileRead + '_revert', 'wb')
forIndexFile = open(fileRead + '_forward', 'wb')

allKeys = sorted(revertIndex.keys())
for key in allKeys:
    values = sorted(list(revertIndex[key]))
    keyLength = len(key)
    bytearr = struct.pack('I{}sI{}I'.format(keyLength, len(values)), keyLength, key, len(values), *values)
    revIndexFile.write(bytearr)

allKeys = sorted(forwardIndex.keys())
for key in allKeys:
    docInf = forwardIndex[key]
    bytearr = struct.pack('II{}sI{}s'.format(len(docInf.title), len(docInf.url)),
                             key, len(docInf.title), docInf.title, len(docInf.url), docInf.url)
    forIndexFile.write(bytearr)

print "--- %s all time" % (time.time() - start_time)

f.close()




 




