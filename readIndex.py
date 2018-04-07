# -*- encoding: utf-8 -*-

import unidecode
import unicodedata
import sys
import json
import string
import re
import time
import os
import struct


class docInfo:
    title = ''
    url = ''
    def __init__(self, title, url):
        self.title = title
        self.url = url
    def __str__(self):
        return self.title + " " + self.url

fileRevert = sys.argv[1]
fileForward = sys.argv[2]

r = open(fileRevert, 'rb')
f = open(fileForward, 'rb')

def skipBytes(f, lenWord):
    read_word = 0
    if lenWord % 4 != 0:
        read_word = 4 - lenWord % 4
    f.read(read_word)

def readPosting(r):
    raw_len_word = r.read(4)
    if raw_len_word == '':
        return (False, "", [])

    len_word = struct.unpack('<I', raw_len_word)[0]

    word = struct.unpack('{}s0'.format(len_word), r.read(len_word))[0]
    skipBytes(r, len_word)

    countEntries = struct.unpack('<I', r.read(4))[0]
    list_entries = list(struct.unpack('<{}I'.format(countEntries), r.read(4 * countEntries)))

    return (True, word, list_entries)

def readForwardDocs(f):
    raw_doc_id = f.read(4)
    if raw_doc_id == '':
        return (False, 0, "", "")
    doc_id = struct.unpack('<I', raw_doc_id)[0]

    len_title = struct.unpack('<I', f.read(4))[0]   
    doc_title = struct.unpack('{}s0'.format(len_title), f.read(len_title))[0]
    skipBytes(f, len_title)

    len_url = struct.unpack('<I', f.read(4))[0]
    doc_url = struct.unpack('{}s0'.format(len_url), f.read(len_url))[0]

    return (True, doc_id, doc_title, doc_url)
    
readyRevertIndex = dict()
readyForwardIndex = dict()
flag = True
while flag:
    flag, word, posting = readPosting(r)
    readyRevertIndex[word] = posting

flag = True
while flag:
    flag, doc_id, doc_title, doc_url = readForwardDocs(f)
    readyForwardIndex[doc_id] = docInfo(doc_title, doc_url)

idSet = readyRevertIndex["путин"]
for i in idSet:
    print readyForwardIndex[i]

