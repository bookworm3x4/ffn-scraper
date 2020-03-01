# ffn scraper.py
# scrapes html from Fanfiction.net pages to generate text files
# of works in Markdown, for conversion to ebook using calibre

# import packages
import requests
from bs4 import BeautifulSoup as bs
from datetime import datetime

def main():
    intro()
    url = getFicUrl()
    soup = getHtml(url)
    soup = checkPage(soup)
    t, m = getMetadata(soup)
    c = getContents(url)
    createTextFile(t, m, c)
    calibreHelp()

def intro():
    print('''Welcome to FFN Scraper!

This program will scan a work on FanFiction.Net and convert
it to a .txt file suitable for ebook conversion in calibre.

Go to the work you want and find the 7-digit ID, either in
the URL or at the end of the description.
''')

def getFicUrl():
    # initialize program with fic URL
    ficID = input("Fic ID is: ")
    ficUrl = 'https://www.fanfiction.net/s/' + ficID + "/"
    print("\nAccessing work at " + ficUrl + "...")
    return ficUrl

def getHtml(url):
    # pulls html from given page
    ### add try/except for ConnectionError (if no internet)
    page = requests.get(url)
    soup = bs(page.content, 'lxml')
    return soup

def checkPage(soup):
    # check if this page has a fic at it, if not iterate through get/check again
    if soup.find(class_="gui_warning") == None:   
        print("Work located. Scanning...")
        return soup
    else:
        print("There doesn't seem to be anything at that location.")
        print("Double-check the URL and try again?")
        url = getFicUrl()
        soup = getHtml(url)
        checkPage(soup)

def getMetadata(soup):
    # finds title, author, and blurb
    title = soup.select("#profile_top b")
    title = str(title[0]).replace('<b class="xcontrast_txt">', '').replace('</b>','')

    author = soup.select("#profile_top a")
    author = str(author[0])
    loc1 = author.find('">') + 2
    loc2 = author.find('</a>')
    author = author[loc1:loc2]

    description = soup.select("#profile_top div")
    description = str(description[1])
    loc1 = description.find('">') + 2
    loc2 = description.find('</div>')
    description = description[loc1:loc2]

    # finds other work info
    infoSoup = soup.select("#profile_top span")[3:]
    info = ""
    for item in infoSoup:
        info += str(item)
    # dictionary holds metadata labels and start/end criteria for trimming them
    infoQuest = {"rating": ['"rating">', '</a>'],
                 "language": [' - ', ' - '],
                 "genres": [' - ', ' - '],
                 "characters": [' - ', ' - '],
                 "chapters": ['Chapters: ', ' - '],
                 "words": ['Words: ', ' - '],
                 "reviews": ['Reviews: ', ' - '],
                 "favs": ['Favs: ', ' - '],
                 "follows": ['Follows: ', ' - '],
                 "updated": ['Updated: ', ' - '],
                 "published": ['Published: ', ' - '],
                 "status": ['Status: ', ' - ']}
    # finds each datum's location and trims it out of its surroundings
    for datum in infoQuest:
        start = infoQuest[datum][0]
        stop = infoQuest[datum][1]
        loc1 = info.find(start)
        if loc1 == -1: # some data do not exist
            value = ""
        else:
            loc1 += len(start)
            info = info[loc1:]
            loc2 = info.find(stop)
            value = info[:loc2]
            info = info[loc2:]
        value = value.strip()
        infoQuest[datum] = value
    # adds current date
    day = datetime.today().day
    month = datetime.today().month
    year = datetime.today().year
    infoQuest["downloaded"] = [day, month, year]
    # makes metadata look pretty
    if infoQuest["chapters"] == '':
        infoQuest["chapters"] = '1'
    for datum in ["reviews", "updated", "published"]:
        # strip away html
        value = infoQuest[datum]
        loc1 = value.find('>') + 1
        value = value[loc1:]
        loc2 = value.find('<')
        value = value[:loc2]
        infoQuest[datum] = value
    for datum in ["chapters", "words", "reviews", "favs", "follows"]:
        # convert to int
        value = infoQuest[datum]
        value = value.replace(',','')
        if value == '':
            value = 0
        else:
            value = int(value)
        infoQuest[datum] = value
    for datum in ["updated", "published"]:
        # convert to nice date
        value = infoQuest[datum]
        value = value.split('/')
        if len(value) == 1:
            value = ''
            infoQuest[datum] = value
        else:
            if len(value) == 3:
                mon, day, year = value
            else:
                mon, day = value
                year = datetime.today().year
            infoQuest[datum] = [day, mon, year]

    # places all gathered metadata into a nice list
    metadata = []
    metadata.append('#' + title)
    metadata.append('###by ' + author)
    metadata.append('###_' + description + '_')
    metadata.append(infoQuest)

    return title, metadata

def getContents(url):
    print("\nCopying contents (this might take a minute)...")
    contents = []

    # pulls text chapter-by-chapter
    i = 1
    while True:
        page = requests.get(url + str(i))
        soup = bs(page.content, 'lxml')
        
        chapTitle = soup.select("option[selected]")
        if chapTitle == []:
            break # exits loop once given chap number returns an error page
        chapTitle = str(chapTitle[0])
        loc1 = chapTitle.find('">') + 2
        loc2 = chapTitle.find('</option>')
        chapTitle = chapTitle[loc1:loc2]
        chapTitle = '##' + chapTitle

        # creates list to hold chapter contents
        chapter = [chapTitle]
        for item in soup.select('p'):
            item = cleanUp(item)
            chapter.append(item)
        
        contents.append(chapter)
        print("X", end="")
        i += 1

    # if work is only one chapter, pulls text differently
    if len(contents) == 0:
        page = requests.get(url)
        soup = bs(page.content, 'lxml')
        
        for item in soup.select('p'):
            item = cleanUp(item)
            contents.append(str(item))
            
    print("FanFiction.Net work has been copied!")
    return contents

def cleanUp(item):
    item = str(item)
    # remove simple tags, replace with markdown
    replacements = [['<p>',''], ['</p>',''],
                    ['<em>','_'], [' </em>','</em> '], ['</em>','_'],
                    ['<strong>','__'], [' </strong>','</strong> '], ['</strong>','__'],
                    ['…','...']]
    for fix in replacements:
        item = item.replace(fix[0], fix[1])
    # remove tags that have additional stuff in them
    ### need to test this new code
    while True:
        loc1 = item.find('<')
        if loc1 == -1:
            break
        else:
            sub = item[loc1:]
            loc2 = sub.find('>')
            loc2 += loc1 + 1
            item = item[:loc1] + item[loc2:]
    return item

def createTextFile(title, metadata, contents):
    print("\nCreating text file...")
    # create text file to hold contents
    fileName = ""
    title = title.split()
    for word in title:
        fileName += word + "_"
    fileName = fileName[:-1] + ".txt"
    textFile = open(fileName,"w+")

    # place title, author, blurb at start of file
    print('<span id="info">', file=textFile)
    for item in metadata[:3]:
        print(item, file=textFile)
    print('', file=textFile)
    
    # place other metadata next
    for item in metadata[3]:
        value = metadata[3][item]
        if type(value) is list:
            day, mon, year = value
            toPrint = item + ": " + str(day) + "/" + str(mon) + "/" + str(year)
        else:
            if value == '':
                continue
            value = str(value)
            toPrint = item + ": " + value
        print(toPrint, file=textFile)
    print('</span>', file=textFile)

    # place contents into file
    print('<span id="contents">', file=textFile)
    if type(contents[0]) == str: # for one-chapter works
        for line in contents:
            print(line, file=textFile)
    else: # for multi-chapter works
        for chapter in contents:
            print(chapter[0], file=textFile)
            print("", file=textFile)
            for line in chapter[1:]:
                print(line, file=textFile)
            print("", file=textFile)
    print('</span>', file=textFile)

    # close the file
    textFile.close()

    print("Work has been saved to " + fileName + ".")

def calibreHelp():
    print()
    print("Would you like instructions on converting the text")
    print("file to a .mobi in calibre? y/n")
    while True:
        wantHelp = input().upper()
        if wantHelp == "Y":
            print(settings)
            input("Hit ENTER to continue...")
            print(helpText)
            break
        elif wantHelp == "N":
            print("Happy reading!")
            break
        else:
            print("Please type Y for yes or N for no.")

# calibre instructions
settings = '''
Go into calibre preferences and apply the following
conversion settings:

Structure detection:
   • Detect chapters at: //h:h2
   • Insert page breaks before: //h:span

Table of Contents:
   • Level 1 TOC: //h:h2

TXT input:
   • Paragraph style: single
   • Formatting style: markdown

MOBI output:
   • Put generated Table of Contents...: yes
'''
helpText = '''
1) Open the .txt file in calibre.

2) Manually update metadata, including adding a cover
image if desired.

3) Select work and click 'Convert books'.
'''

main()
