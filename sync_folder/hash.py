from checksumdir import dirhash
import hashlib
import os
import re
import json
import sys

class HashGenerator:
    #
    # CHECK DIR PATH
    #
    def __init__(self,base_dir = None, get_tree_hash_en=True):
        #-------------------------- VARS
        self.base_dir = base_dir

        #-------------------------- CHECKERS
        self.__check_dir__(base_dir)
        self.folder_separator = "/" if sys.platform == "linux" else "\\"
        self.json_hash = {}
        self.hash_data = {}
        if self.base_dir and get_tree_hash_en:
            self.get_tree_hash()

    #
    # CHECK DIR PATH
    #
    def __check_dir__(self,path):
        try:
            if path and not os.path.isdir(path):                                    #----> If path is not None, and it doesn't exists
                raise Exception("Path "+path+" doesn't exist. Check it out!!!")
        except Exception as e:
            print(e)
            raise

    #
    # CHECK DIR PATH
    #
    def __check_file__(self,path,en_exception=False):
        try:
            *base_dir,file_name = path.split(self.folder_separator)                 #----> Separate dir_folder from file
            base_dir = self.folder_separator.join([item for item in base_dir])      #----> Concatenate name folders to get path
            self.__check_dir__(base_dir)                                            #----> Check if dir_path exists
            if path and not os.path.isfile(path):                                   #----> Check if file exists
                if en_exception:
                    raise Exception("File "+path+" doesn't exist")
                else:
                    print("File doesn't exist.\n Creating it in...\n"+path)
                    with open(path,"w+") as json_file:
                        pass
        except Exception as e:
            print(e)
            raise

    #
    # GENERATE FOLDER HASH
    #
    def __get_folder_hash(self,base_dir):
        #print("HASH FOLDER",base_dir)
        return dirhash(os.path.abspath(base_dir),'md5')

    #
    # GENERATE FILE HASH
    #
    def __get_file_hash(self,base_dir):
        m = hashlib.md5()
        with open(os.path.abspath(base_dir),"rb",buffering=0) as f:
            m.update(f.read())
        return m.hexdigest()

    #
    # GENERATE HASH
    #
    def generate_hash(self,base_dir=None,en_recursive=True,verbose=False):
        if not base_dir:
            base_dir = self.base_dir

        *base_name,folder_name = os.path.abspath(base_dir).split(self.folder_separator)
        folder_name = folder_name.replace('../','').replace('./','').replace('/','')

        hash_data = {folder_name:{}}
        hash_data[folder_name].update({"folder_hash":self.__get_folder_hash(os.path.relpath(base_dir))})

        if verbose:
            print("FOLDER -->", os.path.relpath(base_dir))

        for item in os.listdir(base_dir):
            if os.path.isdir(base_dir+self.folder_separator+item):
                if en_recursive and not re.match(r"\.|__",item):
                    hash_data[folder_name].update(self.generate_hash(os.path.relpath(base_dir+self.folder_separator+item),verbose=verbose))
            else:
                if verbose:
                    print("FILE   -->", os.path.relpath(base_dir+self.folder_separator+item))
                hash_data[folder_name].update({item:self.__get_file_hash(os.path.relpath(base_dir+self.folder_separator+item))})


        return hash_data

    #
    # GENERATE JSON
    #
    def get_tree_hash(self,base_dir=None,save_to_file="",verbose=False):
        self.json_hash = json.dumps(self.generate_hash(base_dir=base_dir,verbose=verbose))
        if save_to_file:
            self.__check_file__(save_to_file)
            with open(save_to_file,"w+") as json_file:
                json_file.write(self.json_hash)
            print("File written!")
        return self.json_hash

    #
    # LOAD JSON
    #
    def set_tree_hash(self,hash_data={},file_to_json=""):
        try:
            if file_to_json:
                self.__check_file__(file_to_json,en_exception=True)
                with open(file_to_json,"r") as json_file:
                    self.json_hash = json_file.read()
                    self.hash_data = json.loads(self.json_hash)
            elif json_hash:
                self.hash_data = hash_data
            else:
                raise Exception("Must pass a dictionary or a file")
        except Exception as e:
            print(e)
            raise
