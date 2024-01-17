import os,zipfile

def addfile(zf, file):
    print(file)
    zf.write(file, file)

with zipfile.ZipFile('pcmpackage.zip', 'w', compression=zipfile.ZIP_DEFLATED) as zf:
    addfile(zf, 'metadata.json')
    addfile(zf, 'resources/icon.png')
    addfile(zf, 'plugins/__init__.py')
    addfile(zf, 'plugins/gerber_zipper_action.py')
    files = os.listdir('plugins/Locale')
    for file in files:
        addfile(zf, 'plugins/Locale/' + file)
    files = os.listdir('plugins/Manufacturers')
    for file in files:
        addfile(zf, 'plugins/Manufacturers/' + file)
    print('pcmpackage.zip complete')
