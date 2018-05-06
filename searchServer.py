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
import vbcode
import math
import operator

app = Flask(__name__)

# класс для информации о документе, нужен в прямом индексе для вывода ответа
class docInfo:
    title = ''
    url = ''
    def __init__(self, title, url, docLen):
        self.title = title
        self.url = url
        self.docLen = docLen
    def __str__(self):
        return self.title + " " + self.url

# загрузка словаря лематизации
def loadLemmaDict():
    lemmaDict = dict()
    f1 = open("uniq_words_union", 'r')
    f2 = open("norm_stem", 'r')
    for line in f1:
        line2 = f2.readline()
        lemmaDict[line[:-1]] = line2[:-1]
    return lemmaDict

# убираем ударения и прочие ненужные символы, заменяем их на обычные
def remove_accents(input_str):
    nkfd_form = unicodedata.normalize('NFKD', input_str)
    return u"".join([c for c in nkfd_form if not unicodedata.combining(c)])

# Просто стэк
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

# вычисление сколько байт нужно пропустить чтобы файловая переменная выровнялась по 4 байта
def skipBytes(lenWord):
    read_word = 0
    if lenWord % 4 != 0:
        read_word = 4 - lenWord % 4
    return read_word

# чтение сжатого постинга из текущей позиции
def readPosting(r):
    # читаем первую длину слова пока можем
    raw_len_word = r.read(4)
    if raw_len_word == '':
        return (False, "", dict())

    # если прочли запоминаем длину слова
    len_word = struct.unpack('<I', raw_len_word)[0]

    # прочитали слово
    word = struct.unpack('{}s0I'.format(len_word), r.read(len_word + skipBytes(len_word)))[0]

    # прочитали длину компрессованных данных
    lenCompressed = struct.unpack('<I', r.read(4))[0]

    # прочитали зажатую строку
    compressed = struct.unpack('{}s0I'.format(lenCompressed), r.read(lenCompressed + skipBytes(lenCompressed)))[0]
    # раскодировка данных
    decompressed = vbcode.decode(compressed)

    # количество постинг листов
    countEntries = decompressed[0]

    # создание пустого постинга (docID-entries)
    entries = dict()

    # получаем зоны
    zonesList = decompressed[1:countEntries + 1]
    # индекс начала списков вхождений
    j = 2 * countEntries + 1
    # обновляем докайди промежутками
    k = 0
    for i in xrange(countEntries + 1, 2 * countEntries + 1):
        decompressed[i] += decompressed[i - 1]
        docId = decompressed[i]
        inZone = zonesList[k]
        k += 1
        if inZone == 1:
            if docId not in zoneIndex:
                zoneIndex[docId] = {word}
            else:
                zoneIndex[docId].add(word) 
        else:
            if docId not in zoneIndex:
                zoneIndex[docId] = set()
            
        

    # обработка списков вхождений и постингов
    for i in xrange(countEntries + 1, 2 * countEntries + 1):
        # запоминание постинга (docID)
        docId = decompressed[i]
        # создание пустого списка для позиций
        entries[docId] = list()
        # берем очередную длину списка вхождений для docId
        lenEntries = decompressed[j]
        # индекс начала списка вхождений 
        j += 1
        # обновление промежутков вхождений
        for k in xrange(j + 1, j + lenEntries):
            decompressed[k] += decompressed[k - 1]
        # обновление списка вхождений
        entries[docId].extend(decompressed[j : j + lenEntries])
        # смещение индекса на начало следующего списка вхождений (а именно на значение длинны следующего списка)
        j += lenEntries

    return (True, word, entries)

def readForwardDocs(f):
    # читаем первую длину слова пока можем
    raw_doc_id = f.read(4)
    if raw_doc_id == '':
        return (False, 0, "", "", 0)

    # чтение информации о статье
    doc_id = struct.unpack('<I', raw_doc_id)[0]
    len_title = struct.unpack('<I', f.read(4))[0]
    doc_title = struct.unpack('{}s0I'.format(len_title), f.read(len_title + skipBytes(len_title)))[0]
    len_url = struct.unpack('<I', f.read(4))[0]
    doc_url = struct.unpack('{}s0I'.format(len_url), f.read(len_url + skipBytes(len_url)))[0]
    docLen = struct.unpack('<I', f.read(4))[0]
    return (True, doc_id, doc_title, doc_url, docLen)

# упрощает слово (убирает капитализацию, ударения, приводит к нормальной форме)
def makeWordSimple(word):
    # - капитализация, - ударения
    word = remove_accents(word.lower()).encode('utf-8')
    # если слово есть словаре лематизации, заменяем его им
    if word in lemmaDict:
        word = lemmaDict[word]
    return word

# Отрицание результата 
def negate(res, substr):
    if substr == True:
        return allDocIds - res
    else:
        return res

# извлечение постинга из слова
def extractPostingForWord(word):
    # если слово не было прочитано ранее
    if word not in cacheForSearch:
        # находим позицию на диске
        pos = readyRevertIndex[word]
        # смещение в нужную позицию
        r.seek(pos)
        # чтение постинга из позиции
        suc, word, posting = readPosting(r)
        # обновление кэша поиска прочитанным постингом
        cacheForSearch[word] = posting
        return posting
    else:
        # возращаем из кэша
        return cacheForSearch[word]

# возвращает docID для слова с учетом отрицания
def returnSetIndexFromWord(word, substr):
    res = set()
    # если слово есть на диске
    if word in readyRevertIndex:
        # извлекаем постинг, а из него все docID, из которых составляем сэт
        res = set(extractPostingForWord(word).keys())
    # вычисление набора с учетом отрицания
    return negate(res, substr)

# обновление индексов при поиске цитат
def updateIndexes(quotes, docID, distance):
    # начальные индексы для каждого слова
    indexes = list()
    for q in quotes:
        indexes.append(0)

    # составление списка списков всех вхождений слов из цитаты 
    entries = [extractPostingForWord(q)[docID] for q in quotes]
    # составление списка позиций соответствующих начальным индексам
    positions = list()
    for i in xrange(len(indexes)):
        index = indexes[i]
        positions.append(entries[i][index])


    while True:
        for i in xrange(1, len(indexes)):
            if positions[i] > positions[i-1]:
                continue
            else:
                while indexes[i] < len(entries[i]) and entries[i][indexes[i]] < positions[i-1]:
                    indexes[i] += 1
                if indexes[i] >= len(entries[i]):
                    return False
                positions[i] = entries[i][indexes[i]]
        if (positions[-1] - positions[0]) <= distance:
            return True
        else:
            indexes[0] += 1
            if indexes[0] >= len(entries[0]):
                return False
            positions[0] = entries[0][indexes[0]]

    return True

# поиск цитат   
def findQuotesDocIds(quotes, commonDocIds, distInt):
    res = set()
    # если дистанция меньше исходного количества слов то возвращаем пустой сэт
    if (distInt < len(quotes)):
        return res
    # если цитата из одного слова - возвращаем список docID's для это слова
    if (len(quotes) == 1):
        return set(commonDocIds)

    # поиск цитаты среди общих документов, где встречались все слова одновременно
    for docId in commonDocIds:
        # поиск цитаты в docID
        flag = updateIndexes(quotes, docId, distInt)
        if flag == True:
            # цитата есть в документе, добавляем docID
            res.add(docId)

    print "answerDocIds: {}".format(res)
    return res
        
# основная функция поиска
def returnSetIntersection(l):
    # обработка терма
    if l[0] not in ops:
        word = l[0]
        substr = False
        # определение отприцания
        if word[0] == '!':
            substr = True
            word = word[1:]

        # массив для слов цитаты
        quote = []
        countQuotes = word.count('"')
        # если цитата (количество кавычек в запросе = 2)
        if countQuotes == 2:
            # позиции кавычек
            quotePos = []
            for m in re.finditer('"', word):
                quotePos.append(m.start());
            
            # отделение содержимого кавычек от кавычек
            words = word[quotePos[0] + 1 : quotePos[1]]

            # хвост цитаты (то что после кавычек - дистанция)
            tail = ""

            #парсинг внутри кавычек
            quote = re.findall(u'[a-zа-яА-ЯA-Z0-9]+|\d+(?:[-,.]\d+)*', words)
            # обработка слов цитаты
            quote = [makeWordSimple(q) for q in quote]
            print quote

            # определение дистанции
            distInt = len(quote)
            if len(word) > (quotePos[1] + 1):
                tail = word[quotePos[1]+1:]
                distString = re.findall('\d+', tail)[0]
                distInt = int(distString)
        
            # множество для поиска общих документов
            resSet = set()
            # поиск общих документов
            if quote.count != 0:
                firstWord = quote[0]
                resSet = returnSetIndexFromWord(firstWord, False)
                for q in quote:
                    resSet = resSet & returnSetIndexFromWord(q, False)

            commonDocIds = list(resSet)
            commonDocIds.sort()
            print 'commonDocIdsCount:'
            print len(commonDocIds)
            # поиск цитаты по общим документам с указанной дистанцией (по-умолчанию дистанция = количеству слов цитаты)
            return negate(findQuotesDocIds(quote, commonDocIds, distInt), substr)

        # слово - не цитата, берем и упрощаем его
        word = makeWordSimple(word)
        # поиск документов содержащих данное слово
        return returnSetIndexFromWord(word, substr)        
    else:
        # хитрое разделение запроса на 2 части
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

        # вернуть результат для левой и правой части
        left = returnSetIntersection(l[1:start])
        right = returnSetIntersection(l[start:])
        
        # применить соответствующую операцию
        if l[0] == '&':
            return (left & right)
        elif l[0] == '|':
            return (left | right)

# получение обратной польской записи через стэк
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

def boolSearch(elements):
    # вставка & в пустых местах
    i = 0
    while i < len(elements) - 1:
        l1 = elements[i]
        l2 = elements[i+1]
        if (l1 not in ops or l1 == ')') and (l2 not in ops or l2 == '('):
            elements.insert(i+1, '&')
        i += 1

    # получение обратной записи
    answer = getReversed(elements)
    
    # получение результата поиска
    resDocs = list(returnSetIntersection(answer))

    scores = dict()
    for docId in resDocs:
        scores[docId] = 0
    
    terms = [el for el in elements if el not in ops]
    terms = set(terms)
    for t in terms:
        t = makeWordSimple(t)
        post = extractPostingForWord(t)

        idf = math.log(allDocsCount / len(post.keys()))
        for docId in post.keys():
            if docId in scores:
                tf = len(post[docId])
                wf = 0
                if tf > 0:
                    wf = 1 + math.log(tf)
                wfidf = wf * idf

                scores[docId] += wfidf

    sorted_scores = sorted(scores.iteritems(), key=operator.itemgetter(1), reverse=True)
    return [score_id for score_id, score_num in sorted_scores]

def blurrySearch(elements):
    scores = dict()
    terms = set(elements)
    for t in terms:
        t = makeWordSimple(t)
        post = extractPostingForWord(t)

        idf = math.log10(allDocsCount / len(post.keys()))
        print idf
        for docId in post.keys():
            tf = len(post[docId])
            wf = 0
            if tf > 0:
                wf = 1 + math.log10(tf)
            wfidf = wf * idf
            
            if docId not in scores:
                scores[docId] = wfidf
            else:
                scores[docId] += wfidf

            if t in zoneIndex[docId]:
                scores[docId] += wfidf

    
    # for docId in scores.keys():
    #     l = readyForwardIndex[docId].docLen
    #     scores[docId] /= l
    
    sorted_scores = sorted(scores.iteritems(), key=operator.itemgetter(1), reverse=True)
    print sorted_scores[:20]
    return [score_id for score_id, score_num in sorted_scores]


# обработка запроса
def getQueryResult(expr):
    #парсинг запроса
    elements = re.findall(u'!?"[a-zA-Zа-яА-Я0-9\s]+"(?:\d+)?|!?\d+(?:[-,.]\d+)*|!?[a-zа-яА-ЯA-Z0-9]+|[&|()]', expr)
    for j in elements:
        print j
    
    isBoolSearch = False
    for el in elements:
        if el in ops:
            isBoolSearch = True
            break
    
    for j in elements:
        print j

    resDocsForUser = []

    if isBoolSearch:
        resDocsForUser = boolSearch(elements)
    else: 
        print 'blurry search'
        resDocsForUser = blurrySearch(elements)

    # составление выдачи по docID's
    return [readyForwardIndex[docId] for docId in resDocsForUser]

# стартовая страница
@app.route('/')
def hello_world():
    return render_template('search.html')

# роутинг для получения запроса
@app.route('/q', methods = ['POST', 'GET'])
def getRes():
    # получение результата из формы по кнопе отправить и редирект на страницу выдачи
    if request.method == 'POST':
        q = request.form['q']
        return redirect(url_for('showRes', query = q, page = 1))
    else:
        q = request.args.get('q')
        return redirect(url_for('showRes', query = q, page = 1))

# роутинг для генерации страницы выдачи
@app.route('/q/<query>/<page>')
def showRes(query, page):
    print "query = %s" % query
    start_time = time.time()
    # получение docID удовлетворяющих запросу
    res = getQueryResult(query)

    print 'количество документов: {}'.format(len(res))

    print "--- %s search time" % (time.time() - start_time)

    res = [docInfo(unicode(r.title, 'utf-8'), unicode(r.url, 'utf-8'), r.docLen) for r in res]
    
    pages = []
    count = len(res) / 50
    mod = len(res) % 50

    numPages = min(5, count)
    # if page > (numPages + 1):
    #     return "Error: out of range"

    res = res[(int(page)-1)*50:int(page)*50]

    pages = [i for i in range(1, numPages + 1)]
    return render_template('search.html', docs=res, q=query, nums=pages)

# файл для обратного индекса (бинарный)
fileRevert = sys.argv[1]
# файл для прямого индекса (бинарный)
fileForward = sys.argv[2]
# файл для позиций слов на диске (слово - f.tell())
fileWordPod = sys.argv[3]

# открытие файлов
r = open(fileRevert, 'rb') 
f = open(fileForward, 'rb')
wordPos = open(fileWordPod, 'r')

# словарь для хранения позиций на диске откуда считывать постинги
readyRevertIndex = dict()
# словарь для прямого индекса, полностью храним в ОП
readyForwardIndex = dict()
# словарь для кэша слов запроса
cacheForSearch = dict()
# словарь для зон
zoneIndex = dict()

# загрузка словаря лематизации
lemmaDict = loadLemmaDict()

# заполнение словаря позиций слов на диске
for line in wordPos:
    word, pos = line.split(" ")
    readyRevertIndex[word] = int(pos)
    
# заполнение словаря прямого индекса
flag = True
while flag:
    flag, doc_id, doc_title, doc_url, doc_len = readForwardDocs(f)
    readyForwardIndex[doc_id] = docInfo(doc_title, doc_url, doc_len)

# все docID документов
allDocIds = set(readyForwardIndex.keys())
allDocsCount = len(allDocIds)

# операнды для парсинга
ops = ["&", "|", ")", "("]

# запуск приложения
if __name__ == '__main__':
    app.run()


