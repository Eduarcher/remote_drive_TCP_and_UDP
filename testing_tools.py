import os
import shutil
import sys
import filecmp


def delete_files(folder):
    """
    Deletes all files in the folder
    :param folder: Folder to delete files
    :return: 0 if success and -1 if failed
    """
    print("Deleting files on", folder)
    for filename in os.listdir(folder):
        print("Deleting:", filename)
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e)),
            return -1
    return 0


def compare_files(folder1, folder2):
    """
    Compares all files in two folder
    :param folder1: Output folder (folder with less files)
    :param folder2: Input folder (folder with MORE files)
    :return: 0 if success and -1 if failed
    """
    print("Comparing files on", folder1, "and", folder2)
    for filename in os.listdir(folder2):
        print("Comparing:", filename, end=' --> ')
        try:
            print(filecmp.cmp(os.path.join(folder1, filename), os.path.join(folder2, filename)))
        except Exception as e:
            print('Failed to compare %s. Reason: %s' % (filename, e))
            return -1
    return 0


def __usage(file):
    print("usage: python", file, "<function: delete|compare> <folder1> <folder2 (compare only)>")
    sys.exit()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        __usage(sys.argv[0])
    if sys.argv[1] == 'delete':
        delete_files(sys.argv[2])
    elif sys.argv[1] == 'compare':
        compare_files(sys.argv[2], sys.argv[3])
    else:
        print("Unknown Function")
