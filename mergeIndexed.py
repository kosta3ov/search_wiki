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

fileRead1 = sys.argv[1]
fileRead2 = sys.argv[2]
fileMerged = sys.argv[3]

r1 = open(fileRead1, 'rb')
r2 = open(fileRead2, 'rb')
w = open(fileMerged, 'wb')

def skipBytes(lenWord):
    read_word = 0
    if lenWord % 4 != 0:
        read_word = 4 - lenWord % 4
    return read_word

def packPosting(word, entr1, entr2, zones1, zones2):
    values1 = sorted(entr1.keys())
    values2 = sorted(entr2.keys())

    l = 0
    r = 0

    entr = dict()
    zones = []
    k = 0

    while l < len(values1) or r < len(values2):
        if l >= len(values1):        
            entr[values2[r]] = entr2[values2[r]]
            zones.append(zones2[r])
            r += 1
        elif r >= len(values2):
            entr[values1[l]] = entr1[values1[l]]
            zones.append(zones1[l])
            l += 1
        else:
            if values1[l] < values2[r]:
                entr[values1[l]] = entr1[values1[l]]
                zones.append(zones1[l])
                l += 1
            else:
                entr[values2[r]] = entr2[values2[r]]
                zones.append(zones2[r])
                r += 1

    values = sorted(entr.keys())
    keyLength = len(word)

    skipList = range(0, len(values), int(math.sqrt(len(values))))

    bytearr = struct.pack('I{}s0III'.format(keyLength), keyLength, word, len(values), len(skipList))

    dist_v = list(values)
    for i in reversed(xrange(1, len(dist_v))):
        dist_v[i] = dist_v[i] - dist_v[i - 1]

    list_for_compression = list(zones)
    list_for_compression.extend(dist_v)
    list_for_compression.extend(skipList)

    compressed = vbcode.encode(list_for_compression)
    bytearr += struct.pack('I{}s0I'.format(len(compressed)), len(compressed), compressed)
    
    for v in values:
        compressed = entr[v]
        bytearr += struct.pack('I{}s0I'.format(len(compressed)), len(compressed), compressed)

    w.write(bytearr)



def readPosting(r):

    raw_len_word = r.read(4)
    if raw_len_word == '':
        return (False, "", dict(), list(), list())

    len_word = struct.unpack('<I', raw_len_word)[0]
    word = struct.unpack('{}s0I'.format(len_word), r.read(len_word + skipBytes(len_word)))[0]

    countEntries = struct.unpack('<I', r.read(4))[0]
    skipListLen = struct.unpack('<I', r.read(4))[0]

    lenCompressed = struct.unpack('<I', r.read(4))[0]

    start_time = time.time()
    compressed = struct.unpack('{}s0I'.format(lenCompressed), r.read(lenCompressed + skipBytes(lenCompressed)))[0]


    start_time = time.time()
    decompressed = vbcode.decode(compressed)


    entries = dict()
    zonesList = decompressed[0 : countEntries]

    k = 0
    start_time = time.time()

    for i in xrange(countEntries, 2 * countEntries):
        decompressed[i] += decompressed[i - 1]
        docId = decompressed[i]
        lenEntries = struct.unpack('<I', r.read(4))[0]
        entries[docId] = r.read(lenEntries + skipBytes(lenEntries))



    skipList = decompressed[2 * countEntries: 2 * countEntries + skipListLen]

    return (True, word, entries, skipList, zonesList)

w1 = True
w2 = True

suc1 = True
suc2 = True

entr1 = dict()
entr2 = dict()

word1 = ""
word2 = ""

skip1 = []
skip2 = []

zones1 = []
zones2 = []

while True:
    if w1 == True:
        suc1, word1, entr1, skip1, zones1 = readPosting(r1)
        if suc1 == False:
            break
    if w2 == True:
        suc2, word2, entr2, skip2, zones2 = readPosting(r2)
        if suc2 == False:
            break
    if (word1 < word2):
        packPosting(word1, entr1, dict(), zones1, list())
        w1 = True
        w2 = False
    elif word2 < word1:
        packPosting(word2, dict(), entr2, list(), zones2)
        w1 = False
        w2 = True
    else:
        packPosting(word1, entr1, entr2, zones1, zones2)
        w1 = True
        w2 = True


r = r1
if suc2 == True:
    r = r2

suc, word, entr, skip, zones = readPosting(r)

while suc == True:
    packPosting(word, entr, dict(), zones, list())
    suc, word, entr, skip, zones = readPosting(r)

