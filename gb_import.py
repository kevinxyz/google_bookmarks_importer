#!/usr/bin/env python2.7
import re
import datetime
import time
from optparse import OptionParser

import selenium
import selenium.common
from selenium import webdriver
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary


PARSER = OptionParser()
PARSER.add_option("--firefox-profile-directory",
                  dest="ffprofile",
                  default='/home/kevin/.mozilla/firefox/htnsajq.kevin',
                  help="Firefox profile directory")
PARSER.add_option("--firefox-path",
                  dest='ffpath',
                  default='/usr/local/bin/firefox/bin/firefox',
                  help="Firefox binary/executable path")
PARSER.add_option("--bookmarkfile",
                  dest='bookmarkfile',
                  default='bk.html',
                  help="Exported Google Bookmark file")

ADD_HTML = 'Add a bookmark'


def get_browser_driver(ffprofile, ffpath):
    _profile = webdriver.FirefoxProfile(profile_directory=ffprofile)
    _binary = FirefoxBinary(firefox_path=ffpath)

    driver = webdriver.Firefox(firefox_profile=_profile,
                               firefox_binary=_binary)

    return driver


def wait_for_signin(driver):
    driver.get('https://www.google.com/bookmarks/mark?op=add&hl=en')
    signin_msg = 'Sign in to continue'
    if signin_msg in driver.page_source:
        print 'Please sign in first...'
        while ADD_HTML not in driver.page_source:
            print "Waiting for bookmarks page to come up..."
            time.sleep(2)


def rm_bkmk(driver):
    while True:
        driver.get('https://www.google.com/bookmarks/')
        if 'yet saved' in driver.page_source:
            return

        cnt = 50
        while cnt > 0:
            if 'Remove' not in driver.page_source:
                return  # all done
            time.sleep(0.10)
            cnt -= 1

        while 'Remove' in driver.page_source:
            try:
                driver.find_element_by_link_text('Remove').click()
            except selenium.common.exceptions.NoSuchElementException:
                break
            alertDialog = driver.switch_to_alert()
            alertDialog.accept()


def add_bkmk(driver, title, url, labels, annotation):
    driver.get('https://www.google.com/bookmarks/mark?op=add&hl=en')
    cnt = 50
    while cnt > 0:
        if ADD_HTML in driver.page_source:
            break
        time.sleep(0.10)
        cnt -= 1

    assert "Bookmarks" in driver.title

    title_elem = driver.find_element_by_name('title')
    #title_elem.clear()
    title_elem.send_keys(title)

    bkmk = driver.find_element_by_name('bkmk')
    #bkmk.clear()
    bkmk.send_keys(url)

    if labels:
        labels = [l for l in labels if l != u'Unlabeled']
        if labels:
            labels_elem = driver.find_element_by_name('labels')
            #labels_elem.clear()
            labels_elem.send_keys(','.join(labels))

    if annotation:
        anno = driver.find_element_by_name('annotation')
        #anno.clear()
        anno.send_keys(annotation)

    bar = driver.find_element_by_class_name('kd-button-submit')
    bar.click()

    assert 'Add bookmark' in driver.page_source
    #elem.send_keys(Keys.RETURN)


class Bookmark(object):
    def __init__(self, title, url, annotations, dateseconds, nicedatestamp):
        if title is not None:
            try:
                title = unicode(title, 'utf-8')
            except UnicodeDecodeError:
                pass
        self.title = title

        self.url = url

        if annotations is not None:
            try:
                annotations = unicode(annotations, 'utf-8')
            except UnicodeDecodeError:
                pass
        self.annotations = annotations

        self.labels = []
        self.added_seconds = dateseconds
        self.nicedatestamp = nicedatestamp

    def add_label(self, label):
        try:
            label = unicode(label, 'utf-8')
        except UnicodeDecodeError:
            pass
        self.labels.append(label)

    def __str__(self):
        return "%s %s %s %s" % (self.url,
                                self.title,
                                self.labels,
                                self.nicedatestamp)


def read_bookmarks_and_save(driver, bookmark_file, start_bookmark_pos=0):
    label = added_seconds = nicedatestamp = None
    url2bookmark = {}

    with open(bookmark_file) as fd:
        lines = fd.readlines()
    lines.append('')
    lines.append('')
    line_cnt = -1
    while line_cnt <= len(lines) - 2:
        line_cnt += 1
        # <DT><H3 ADD_DATE="1324687284604357">__init__</H3>
        line = lines[line_cnt]
        #print "HEY %s %s" % (line, line_cnt)
        m = re.search('H3 ADD_DATE="(\d+)">([^<]*)<', line, re.I)
        if m:
            added_seconds, label = m.group(1, 2)
            added_seconds = int(added_seconds)
            nicedatestamp = datetime.datetime.fromtimestamp(
                added_seconds / 1000000).strftime("%Y-%m-%d %H:%M")
            continue

        # <DT><A HREF="http://stackoverflow.com/questions/1675734/how-do-i-create-a-namespace-package-in-python" ADD_DATE="1324687284604357">How do I create a namespace package in Python? - Stack Overflow</A>
        m = re.search('A HREF="([^"]+)" ADD_DATE="\d+">([^>]*)</a>', line, re.I)
        if m:
            url, title = m.group(1, 2)

            next_line = lines[line_cnt]
            mm = re.search('<DD>(.+)', next_line)
            if mm:
                line_cnt += 1
                if re.search('\d{4}\-\d{2}\-\d{2} \d+:\d+', next_line):
                    # use verbatim (datestamp is already embedded)
                    annotations = next_line
                else:
                    # add datestamp along with description
                    annotations = '%s (%s) %s' % (nicedatestamp, added_seconds, mm.group(1))
            else:
                annotations = '%s (%s) %s' % (nicedatestamp, added_seconds, title)

            if url in url2bookmark:
                url2bookmark[url].add_label(label)
            else:
                url2bookmark[url] = Bookmark(title, url, annotations, added_seconds, nicedatestamp)
                url2bookmark[url].add_label(label)

    bookmark_pos = 0
    for i, (url, bookmark) in enumerate(sorted(url2bookmark.iteritems())):
        bookmark_pos += 1
        print "Inserting #%d %s %.2f%%..." % (i, bookmark, 100.0 * i / len(url2bookmark))
        if bookmark_pos >= start_bookmark_pos:
            add_bkmk(driver,
                     bookmark.title,
                     bookmark.url,
                     bookmark.labels,
                     bookmark.annotations)


if __name__ == '__main__':
    (options, args) = PARSER.parse_args()
    driver = get_browser_driver(options.ffprofile, options.ffpath)
    wait_for_signin(driver)
    read_bookmarks_and_save(driver, options.bookmarkfile)
    #rm_bkmk(driver)
    print "Done. Resting for 100 seconds for you to double check..."
    time.sleep(100)
    driver.close()
