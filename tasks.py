import os
from invoke import task, run

@task
def cfuncs():
    run('gcc -Wall -Wextra -O -std=gnu99 -pedantic -fPIC -fvisibility=hidden -shared qtpuzzle/render_outline.c -o qtpuzzle/_render_outline.so')
    
@task
def uic():
    run('pyuic4 qtpuzzle/mainwindow.ui --from-imports  -o qtpuzzle/mainwindowUI.py')
    run('pyuic4 qtpuzzle/shortcut_help.ui --from-imports  -o qtpuzzle/shortcutHelpUI.py')
    run('pyuic4 slicer/slicer.ui -o slicer/slicerUI.py')

@task
def resources():
    run('pyrcc4 -py3 qtpuzzle/icons.qrc -o qtpuzzle/icons_rc.py')

@task(uic, resources, cfuncs)
def all():
    pass

@task(all, default=True)
def puzzle2():
    run('./puzzle2', pty=True)

@task(uic)
def slicer():
    run('python3 slicer_standalone.py')
    
@task
def testboard():
    '''Run puzzleboard service listening on stdin;
    read testcommands.txt and pipe line-by-line to the service.
    '''
    run("cat testcommands.txt | while read CMD; do echo $CMD; sleep 3; done | tee /dev/stderr | python3 -m puzzleboard")
