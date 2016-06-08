import os
from invoke import task, run

@task
def cfuncs():
    run('gcc -Wall -Wextra -O -std=gnu99 -pedantic -fPIC -fvisibility=hidden -shared cfuncs.c -o cfuncs.so')
    
@task(cfuncs)
def cftest():
    run('python3 test_cfuncs.py')
    
@task
def uic():
    run('pyuic4 mainwindow.ui -o mainwindowUI.py')

@task
def resources():
    run('pyrcc4 -py3 icons.qrc -o icons_rc.py')

@task(uic, resources)
def all():
    pass

@task(all, default=True)
def puzzle():
    run('python3 pinhole.py', pty=True)

@task
def slicer():
    run('python3 slicer_standalone.py')