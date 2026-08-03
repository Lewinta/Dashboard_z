# Python 3: the csv module handles unicode natively, so the old Python 2
# UTF8Recoder / unicode() recoding dance is no longer needed. These thin
# wrappers keep the original call sites (UnicodeReader / UnicodeWriter) working.

import csv


class UnicodeReader:
    def __init__(self, f, dialect=csv.excel, encoding="latin-1", **kwds):
        # f is an already-open text-mode file; csv.reader yields lists of str.
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def __next__(self):
        return next(self.reader)

    def __iter__(self):
        return self


class UnicodeWriter:
    def __init__(self, f, dialect=csv.excel, encoding="latin-1", **kwds):
        self.writer = csv.writer(f, dialect=dialect, **kwds)

    def writerow(self, row):
        self.writer.writerow(row)

    def writerows(self, rows):
        self.writer.writerows(rows)
