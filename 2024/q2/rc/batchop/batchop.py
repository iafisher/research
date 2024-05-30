"""
Supported operations:

- delete <fileset>
- rename <pattern1> <pattern2>
- move <fileset> <destination>
- list <fileset>
- replace <pattern1> <pattern2> <fileset>
- run <cmd> <fileset>

Python interface:

    bop = BatchOp()
    bop.delete(FileSet().is_empty().is_folder().is_named("Archive"))

Command-line interface:

    $ batchop 'delete all folders named "Archive" that are not empty'
    $ batchop 'rename %_trip.jpg to %.jpg'

Interactive interface:

    $ batchop
    671 files, 17 folders
    > is a file
    671 files
    > ends with .md
    534 files
    > move to markdown-files

"""
