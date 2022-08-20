import os
from invoke import task, run

@task
def cfuncs():
    raise ValueError()
    run('gcc -Wall -Wextra -O -std=gnu99 -pedantic -fPIC -fvisibility=hidden -shared qtpuzzle/render_outline.c -o qtpuzzle/_render_outline.so')

@task(cfuncs)
def all():
    pass

@task(all, default=True)
def puzzle2():
    run('./puzzle2', pty=True)

@task()
def slicer():
    run('python3 slicer_standalone.py')
    
@task
def testboard():
    '''Run puzzleboard service listening on stdin;
    read testcommands.txt and pipe line-by-line to the service.
    '''
    run("cat testcommands.txt | while read CMD; do echo $CMD; sleep 3; done | tee /dev/stderr | python3 -m puzzleboard")
