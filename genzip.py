import hashlib
import json
import os
import pickle
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
IGNORE_CHARS = ["-", "_", " "]


class ProductData:
    def __init__(self, product_num, zip_name, time_stamp=None):
        self.product_num = product_num
        self.zip_name = zip_name
        self.time_stamp = time_stamp


def is_not_ignore(file):
    not_ignore = True
    not_ignore &= (file != ".DS_Store")
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


def make_manifest(root_path, file_name=MANIFEST_PATH):
    file_list = os.listdir(root_path)
    path_list = []
    if "Content" in file_list:
        recursive_path_enumeration("/".join([root_path, "Content"]), path_list)

    if "content" in file_list:
        recursive_path_enumeration("/".join([root_path, "content"]), path_list)

    if len(path_list) == 0:
        return False, [], ""

    path_list = [path[len(root_path)+1:] for path in path_list]

    root = etree.Element('DAZInstallManifest', VERSION="0.1")
    root.append(etree.Element('GlobalID', VALUE=str(uuid.uuid4())))

    def _append_file(path):
        root.append(etree.Element("File", TARGET="Content", ACTION="Install", VALUE=path))
    [_append_file(path) for path in path_list]

    s = etree.tostring(root, pretty_print=True).decode('utf-8')
    # s = s.replace('ACTION="Install" TARGET="Content"', 'TARGET="Content" ACTION="Install"')
    return True, path_list, s


def make_supplement(root_path, file_name=SUPPLEMENT_PATH):
    root = etree.Element('ProductSupplement', VERSION="0.1")
    root.append(etree.Element('ProductName', VALUE=root_path.split("/")[-1]))
    root.append(etree.Element('InstallTypes', VALUE="Content"))
    root.append(etree.Element('ProductTags', VALUE="DAZStudio4_5"))
    s = etree.tostring(root, pretty_print=True).decode('utf-8')
    return True, s


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


def make_zip_name(dir_path, product_num):
    def _replace_ignore_char(zip_name):
        for ignore_char in IGNORE_CHARS:
            zip_name = zip_name.replace(ignore_char, "")
        return zip_name
    return ZIP_NAME_FORMAT.format(product_num, _replace_ignore_char(dir_path.split("/")[-1]))


def get_md5(root_path, path_list):
    m = hashlib.md5()

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


def make_zipfile(dir_path, product_dict):
    ok_manifest, path_list, manifest_str = make_manifest(dir_path)
    ok_supplement, supplement_str = make_supplement(dir_path)
    if ok_manifest and ok_supplement:
        md5_val = get_md5(dir_path, path_list)
        if md5_val in product_dict:
            product_data = product_dict[md5_val]
        else:
            product_num = get_count()
            zip_name = make_zip_name(dir_path, product_num)
            product_data = ProductData(product_num, zip_name)

        zip_fullpath = os.path.abspath("/".join([OUTPUT_PATH, "{}.zip".format(product_data.zip_name)]))
        if os.path.exists(zip_fullpath):
            print("{} is already exists".format(zip_fullpath))
            return

        with ZipFile(zip_fullpath, 'w') as myzip:
            def _write_zip(rel_path):
                myzip.write("/".join([dir_path, rel_path]), rel_path)
            [_write_zip(path) for path in path_list]
            myzip.writestr(MANIFEST_PATH, manifest_str)
            myzip.writestr(SUPPLEMENT_PATH, supplement_str)
        print("wrote: " + zip_fullpath)
        product_dict[md5_val] = product_data
        save_product_dict(product_dict)


if __name__ == "__main__":
    root_path = os.getcwd()
    product_dict = load_product_dict()
    print(product_dict)
    [make_zipfile("/".join([root_path, INPUT_PATH, file_name]), product_dict)
        for file_name in os.listdir(INPUT_PATH) if not os.path.isfile("/".join([root_path, INPUT_PATH, file_name]))]



