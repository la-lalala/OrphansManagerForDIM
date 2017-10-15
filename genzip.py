import hashlib
import json
import mimetypes
import os
import pickle
import re
import uuid
from lxml import etree
from zipfile import ZipFile

INPUT_PATH = "Inputs"
OUTPUT_PATH = "Outputs"
CONFIG_PATH = "config.json"
PRODUCT_DICT_PATH = "product_dict.pickle"
MANIFEST_PATH = "Manifest.dsx"
SUPPLEMENT_PATH = "Supplement.dsx"

ZIP_NAME_FORMAT = "ORPHANS9{0:07d}-01_{1}"
IGNORE_SYSTEM_FILES = [".DS_Store", "dummy.txt"]
IGNORE_INPUT_FILES = [".DS_Store", ]

TOP_DIRS = ["Content", "content", "My Library"]
SUB_DIRS = [
    "/Animals/",
    "/Camera Presets/",
    "/DAZ Studio Tutorials/",
    "/data/",
    "/Documentation/",
    "/Environments/",
    "/Figures/",
    "/General/",
    "/Light Presets/",
    "/People/",
    "/Presets/",
    "/Props/",
    "/Render Presets/",
    "/Scene Builder/",
    "/Scenes/",
    "/Scripts/",
    "/Shader Presets/",
    "/Runtime/"
]
BASE_DIR_NAME = "content"
REPLACE_TOP_DIRS = ["Content", "My Library"]


class ProductData:
    def __init__(self, product_num, product_name, zip_name, time_stamp=None):
        self.product_num = product_num
        self.product_name = product_name
        self.zip_name = zip_name
        self.time_stamp = time_stamp


def is_not_ignore(file, ignore_files=IGNORE_INPUT_FILES):
    not_ignore = True
    for ignore_file in ignore_files:
        not_ignore &= (file != ignore_file)
    return not_ignore


def recursive_path_enumeration(root_path, path_list):
    file_list = os.listdir(root_path)

    def _dir_or_not(file_name):
        abs_path = "/".join([root_path, file_name])
        if(os.path.isdir(abs_path)):
            recursive_path_enumeration(abs_path, path_list)
        else:
            path_list.append(abs_path)
    [_dir_or_not(file) for file in file_list if is_not_ignore(file)]


def get_read_path_list(root_path, is_zip):
    path_list = []
    if is_zip:
        with ZipFile(root_path, "r") as myzip:
            path_list = myzip.namelist()

            def _ignore(path):
                return path.endswith('/') or path.startswith("__MACOSX")
            path_list = [path for path in path_list if not _ignore(path)]
    else:
        recursive_path_enumeration(root_path, path_list)
        path_list = [path[len(root_path)+1:] for path in path_list]
    return path_list


def get_write_path_list(read_path_list):
    write_path_list = []
    if len(read_path_list) > 0:
        sample_path = read_path_list[0]
        target_dir_name = None
        content_dir_index = -1
        for dir_name in TOP_DIRS:
            content_dir_index = sample_path.find(dir_name)
            if content_dir_index != -1:
                target_dir_name = dir_name
                break
        if content_dir_index != -1:
            def _cut_and_replace(path):
                return path[content_dir_index:] if target_dir_name not in REPLACE_TOP_DIRS else path[content_dir_index:].replace(target_dir_name, "Content")
            write_path_list = [_cut_and_replace(read_path) for read_path in read_path_list]
        else:
            sub_dir_index = -1
            write_path_list = ["".join(["/", read_path]) for read_path in read_path_list]
            for write_path in write_path_list:
                def _find_sub_dir(sub_dir):
                    return write_path.lower().find(sub_dir.lower())
                sub_dir_indexes = [_find_sub_dir(sub_dir) for sub_dir in SUB_DIRS]
                sub_dir_indexes = [index for index in sub_dir_indexes if index != -1]
                if sub_dir_indexes:
                    sub_dir_index = sub_dir_indexes[0]
                    break
            if sub_dir_index == -1:
                return []
            else:
                write_path_list = [write_path[sub_dir_index+1:] for write_path in write_path_list]
                write_path_list = ["/".join(["Content", write_path]) for write_path in write_path_list]

    def _except_one_level_below_file_from_top(path):
        return path if len(path.split("/"))>=3 else None
    write_path_list = [_except_one_level_below_file_from_top(path) for path in write_path_list]
    return write_path_list


def make_manifest(path_list, file_name=MANIFEST_PATH):
    root = etree.Element('DAZInstallManifest', VERSION="0.1")
    root.append(etree.Element('GlobalID', VALUE=str(uuid.uuid4())))

    def _append_file(path):
        root.append(etree.Element("File", TARGET="Content", ACTION="Install", VALUE=path))
    [_append_file(path) for path in path_list if path]

    s = etree.tostring(root, pretty_print=True).decode('utf-8')
    return s


def make_supplement(root_path, file_name=SUPPLEMENT_PATH):
    root = etree.Element('ProductSupplement', VERSION="0.1")
    root.append(etree.Element('ProductName', VALUE="[OM] {}".format(root_path.split("/")[-1])))
    root.append(etree.Element('InstallTypes', VALUE="Content"))
    root.append(etree.Element('ProductTags', VALUE="DAZStudio4_5"))
    s = etree.tostring(root, pretty_print=True).decode('utf-8')
    return s


def get_count():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            json_data = json.load(f)
    else:
        json_data = {"count": 0}
    json_data["count"] = json_data.get("count", 0) + 1
    with open(CONFIG_PATH, "w") as f:
            json.dump(json_data, f)
    return json_data["count"]


def get_md5(root_path, path_list, is_zip):
    m = hashlib.md5()
    if(is_zip):
        with open(root_path, "rb") as f:
            m.update(f.read())
    else:
        def _update_md5(path):
            with open(path, "rb") as f:
                m.update(f.read())
        [_update_md5("/".join([root_path, path])) for path in path_list]
    return m.hexdigest()


def load_product_dict():
    if os.path.exists(PRODUCT_DICT_PATH):
        with open(PRODUCT_DICT_PATH, "rb") as f:
            product_dict = pickle.load(f)
    else:
        product_dict = {}
    return product_dict


def save_product_dict(product_dict):
    with open(PRODUCT_DICT_PATH, "wb") as f:
        pickle.dump(product_dict, f)


def make_zip_name(product_name, product_num):
    def _replace_ignore_char(zip_name):
        return re.sub("[\W_]", "", zip_name)
    return ZIP_NAME_FORMAT.format(product_num, _replace_ignore_char(product_name))


def get_product_data(md5_val, product_name, product_dict):
    if md5_val in product_dict:
        product_data = product_dict[md5_val]
    else:
        product_num = get_count()
        zip_name = make_zip_name(product_name, product_num)
        product_data = ProductData(product_name, product_num, zip_name)
    return product_data


def write_zip(zip_fullpath, input_path, read_path_list, write_path_list, manifest_str, supplement_str, is_zip):
    with ZipFile(zip_fullpath, 'w') as writezip:
        if is_zip:
            with ZipFile(input_path, "r") as readzip:
                def _write_zip(read_path, write_path):
                    writezip.writestr(write_path, readzip.read(read_path))
                [_write_zip(read_path, write_path) for read_path, write_path in zip(read_path_list, write_path_list) if write_path]
        else:
            def _write_zip(read_path, write_path):
                writezip.write("/".join([input_path, read_path]), write_path)
            [_write_zip(read_path, write_path) for read_path, write_path in zip(read_path_list, write_path_list) if write_path]
        writezip.writestr(MANIFEST_PATH, manifest_str)
        writezip.writestr(SUPPLEMENT_PATH, supplement_str)
    print("wrote: " + zip_fullpath)


def make_zipfile(input_path, product_dict):
    is_dir = os.path.isdir(input_path)
    is_zip = mimetypes.guess_type(input_path)[0] == 'application/zip'
    if not (is_dir or is_zip):
        print("Not dir or zip: {}".format(input_path))
        return

    product_name = input_path.split("/")[-1].split(".")[0]
    read_path_list = get_read_path_list(input_path, is_zip)

    if len(read_path_list) == 0:
        print("can't read: {}".format(input_path))
        return
    else:
        md5_val = get_md5(input_path, read_path_list, is_zip)
        product_data = get_product_data(md5_val, product_name, product_dict)
        zip_fullpath = os.path.abspath("/".join([OUTPUT_PATH, "{}.zip".format(product_data.zip_name)]))
        if os.path.exists(zip_fullpath):
            print("already exists: {}".format(zip_fullpath))
            return
        write_path_list = get_write_path_list(read_path_list)
        if len(write_path_list) == 0:
            print("can't find SUB_DIRS(like 'People','Figures' and so on ): {}".format(input_path))
            return
        manifest_str = make_manifest(write_path_list)
        supplement_str = make_supplement(product_name)
        write_zip(zip_fullpath, input_path, read_path_list, write_path_list, manifest_str, supplement_str, is_zip)
        product_dict[md5_val] = product_data
        save_product_dict(product_dict)


if __name__ == "__main__":
    root_path = os.getcwd()
    product_dict = load_product_dict()
    [make_zipfile("/".join([root_path, INPUT_PATH, file_name]), product_dict)
        for file_name in os.listdir(INPUT_PATH) if is_not_ignore(file_name, ignore_files=IGNORE_SYSTEM_FILES)]
