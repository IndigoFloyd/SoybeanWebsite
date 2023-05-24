progress = '0%'
title = ''

def setProgressBar(value):
    global progress
    progress = value

def getProgressBar():
    return progress

def initProgressBar():
    global progress
    progress = '0%'

def setTitle(value):
    global title
    title = value

def initTitle():
    global title
    title = ''

def getTitle():
    return title