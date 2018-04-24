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

def skipBytes(lenWord):
    read_word = 0
    if lenWord % 4 != 0:
        read_word = 4 - lenWord % 4
    return read_word

def skipPosting(r):
    raw_len_word = r.read(4)
    if raw_len_word == '':
        return False, ""
    len_word = struct.unpack('<I', raw_len_word)[0]
    word = struct.unpack('{}s0I'.format(len_word), r.read(len_word + skipBytes(len_word)))[0]
    countEntries = struct.unpack('<I', r.read(4))[0]

    for i in xrange(countEntries):
        compressedLen = struct.unpack('<I', r.read(4))[0]
        r.seek(compressedLen + skipBytes(compressedLen), os.SEEK_CUR)
        
    return True, word

fileRevert = sys.argv[1]
fileWordPod = sys.argv[2]

r = open(fileRevert, 'rb')
wordPos = open(fileWordPod, 'w')

readyRevertIndex = dict()

flag = True
while flag == True:
    pos = r.tell()
    flag, word = skipPosting(r)
    if flag == True:
        wordPos.write("{} {}\n".format(word, str(pos)))

    

