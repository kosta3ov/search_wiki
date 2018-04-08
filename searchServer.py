# -*- encoding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for
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

def loadLemmaDict():
    lemmaDict = dict()
    f1 = open("uniq_words_union", 'r')
    f2 = open("norm_stem", 'r')
    for line in f1:
        line2 = f2.readline()
        lemmaDict[line[:-1]] = line2[:-1]
    return lemmaDict

def remove_accents(input_str):
    nkfd_form = unicodedata.normalize('NFKD', input_str)
    return u"".join([c for c in nkfd_form if not unicodedata.combining(c)])

class Stack:
    def __init__(self):
        self.items = []
    def isEmpty(self):
        return self.items == []
    def push(self, item):
        self.items.append(item)
    def pop(self):
        return self.items.pop()
    def peek(self):
        return self.items[len(self.items)-1]
    def size(self):
        return len(self.items)

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

    entries = dict()

    for i in xrange(countEntries):
        docId = struct.unpack('<I', r.read(4))[0]
        coordsLen = struct.unpack('<I', r.read(4))[0]
        coords = list(struct.unpack('<{}I'.format(coordsLen), r.read(4 * coordsLen)))
        entries[docId] = coords

    return (True, word, entries)

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

def makeWordSimple(word):
    word = remove_accents(word.lower()).encode('utf-8')
    if word in lemmaDict:
        word = lemmaDict[word]
    return word

def negate(res, substr):
    if substr == True:
        return allDocIds - res
    else:
        return res

def returnSetIndexFromWord(word, substr):
    res = set()
    if word in readyRevertIndex:
        res = set(readyRevertIndex[word].keys())
    return negate(res, substr)

def isPostingsNear(posting, pos):
    for elem in posting:
        if elem > pos:
            return False
        else:
            if elem == pos:
                return True
    return False
    
def findQuotesDocIds(quotes, commonDocIds):
    res = set()
    for docId in commonDocIds:
        firstPosting = readyRevertIndex[quotes[0]][docId];
        for pos in firstPosting:
            nextPos = pos + 1
            isFound = True
            for i in xrange(1, len(quotes)):
                p = readyRevertIndex[quotes[i]][docId]
                if isPostingsNear(p, nextPos) == False:
                    isFound = False
                    break
                nextPos += 1
            if isFound == True:
                res.add(docId)
                break
    return res
        
def returnSetIntersection(l):
    if l[0] not in ops:
        word = l[0]
        substr = False
        if word[0] == '!':
            substr = True
            word = word[1:]

        quote = []
        #if quote
        if word[0] == '"' and word[-1] == '"':
            words = word[1:-1]
            #парсинг внутри кавычек
            quote = re.findall(u'[a-zа-яА-ЯA-Z0-9,.]+', words)
            quote = [makeWordSimple(q) for q in quote]
        
            resSet = set()

            if quote.count != 0:
                firstWord = quote[0]
                resSet = returnSetIndexFromWord(firstWord, False)
                for q in quote:
                    resSet = resSet & returnSetIndexFromWord(q, False)
            print "resSet:"
            print resSet
            commonDocIds = list(resSet)
            commonDocIds.sort()
            print commonDocIds
            return negate(findQuotesDocIds(quote, commonDocIds), substr)

        word = makeWordSimple(word)
        return returnSetIndexFromWord(word, substr)        
    else:
        start = 1
        cnt_word_need = 1
        cnt_word_cur = 0
        
        while cnt_word_cur != cnt_word_need:
            new_start = start + cnt_word_need - cnt_word_cur
            for i in range(start, new_start):
                if l[i] not in ops:
                    cnt_word_cur += 1
                else:
                    cnt_word_need += 1
            start = new_start

        left = returnSetIntersection(l[1:start])
        right = returnSetIntersection(l[start:])
        
        if l[0] == '&':
            return (left & right)
        elif l[0] == '|':
            return (left | right)

fileRevert = sys.argv[1]
fileForward = sys.argv[2]
r = open(fileRevert, 'rb')
f = open(fileForward, 'rb')

readyRevertIndex = dict()
readyForwardIndex = dict()
lemmaDict = loadLemmaDict()

flag = True
while flag:
    flag, word, posting = readPosting(r)
    if flag == False:
        break
    readyRevertIndex[word] = posting

flag = True
while flag:
    flag, doc_id, doc_title, doc_url = readForwardDocs(f)
    readyForwardIndex[doc_id] = docInfo(doc_title, doc_url)


allDocIds = set(readyForwardIndex.keys())
ops = ["&", "|", ")", "("]

def getReversed(elements):
    st = Stack()
    answer = []
    
    for el in elements:
        if el not in ops:
            answer.append(el)
        elif el == "(":
            st.push(el)
        elif el == ")":
            while st.peek() != "(":
                answer.append(st.pop())
            st.pop()
        else:
            if st.isEmpty():
                st.push(el)
                continue
            top = st.peek()
            while top != "(":
                answer.append(st.pop())
                if st.isEmpty():
                    break
                else:
                    top = st.peek()
            st.push(el)

    while not st.isEmpty():
        answer.append(st.pop())
        
    answer.reverse()
    return answer

def getQueryResult(expr):
    #парсинг запроса
    elements = re.findall(u'!?"[a-zA-Zа-яА-Я0-9\s.,]+"|!?[a-zа-яА-ЯA-Z0-9,.]+|[&|()]', expr)
    
    i = 0
    while i < len(elements) - 1:
        l1 = elements[i]
        l2 = elements[i+1]
        if (l1 not in ops or l1 == ')') and (l2 not in ops or l2 == '('):
            elements.insert(i+1, '&')
        i += 1

    for j in elements:
        print j

    
    answer = getReversed(elements)
    res = returnSetIntersection(answer)
    
    resDocs = list(res)
    resDocs.sort()
    
    resDocsForUser = []
    for docId in resDocs:
        resDocsForUser.append(readyForwardIndex[docId])
    return resDocsForUser

app = Flask(__name__)

@app.route('/')
def hello_world():
    return render_template('search.html')

@app.route('/q', methods = ['POST', 'GET'])
def getRes():
    if request.method == 'POST':
        q = request.form['q']
        return redirect(url_for('showRes', query = q, page = 1))
    else:
        q = request.args.get('q')
        return redirect(url_for('showRes', query = q, page = 1))

@app.route('/q/<query>/<page>')
def showRes(query, page):
    print "query = %s" % query
    start_time = time.time()
    res = getQueryResult(query)
    print "--- %s search time" % (time.time() - start_time)

    res = [docInfo(unicode(r.title, 'utf-8'), unicode(r.url, 'utf-8')) for r in res]
        
    pages = []
    count = len(res) / 50
    mod = len(res) % 50

    numPages = min(5, count)
    # if page > (numPages + 1):
    #     return "Error: out of range"

    res = res[(int(page)-1)*50:int(page)*50]

    pages=[i for i in range(1,numPages + 1)]
    return render_template('search.html', docs=res, q=query, nums=pages)

if __name__ == '__main__':
   app.run()
