from checksumdir import dirhash
import hashlib
import os
import re
import json
import sys

class Hash:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.json_hash = {}
        self.hash_data = {}
        self.folder_separator = "/" if sys.platform == "linux" else "\\"

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
    def set_folder_hash(self,base_dir):
        #print("HASH FOLDER",base_dir)
        return dirhash(os.path.abspath(base_dir),'md5')

    #
    # GENERATE FILE HASH
    #
    def set_file_hash(self,base_dir):
        m = hashlib.md5()
        with open(os.path.abspath(base_dir),"rb",buffering=0) as f:
            m.update(f.read())
        return m.hexdigest()

    def set_hash(self,base_dir):
        if os.path.isdir(base_dir):
            return self.set_folder_hash(base_dir)
        else:
            return self.set_file_hash(base_dir)

    def set_tree_hash(self,save_to_file="",verbose=False, file_to_json="", hash_data={}):
        if file_to_json:
            self.__check_file__(file_to_json,en_exception=True)
            with open(file_to_json,"r") as json_file:
                self.json_hash = json_file.read()
                self.hash_data = json.loads(self.json_hash)
        elif hash_data:
            self.hash_data = hash_data
            self.json_hash = json.dumps(self.hash_data)
        else:
            print("NO DATA PASSED")

        if save_to_file:
            self.__check_file__(save_to_file)
            with open(save_to_file,"w+") as json_file:
                json_file.write(self.json_hash)
            print("File written!")
        return self.json_hash

    def copy_file(self,source_file,destination_folder):
        cp_linux = "cp -R" if os.path.isdir(source_file) else ""
        copy_cmd = cp_linux if sys.platform == "linux" else "copy"
        copy_cmd = copy_cmd + " " + source_file + " "+ destination_folder
        print("COPY CMD",copy_cmd)
        #os.system(copy_cmd)


class HashGenerator(Hash):
    def __init__(self,base_dir = None, get_tree_hash_en=True):
        super().__init__(base_dir)

        if self.base_dir and get_tree_hash_en:
            self.set_tree_hash()

    #
    # GENERATE HASH
    #
    def generate_hash(self,base_dir=None,en_recursive=True,verbose=False):
        if not base_dir:
            base_dir = self.base_dir

        *base_name,folder_name = os.path.abspath(base_dir).split(self.folder_separator)
        #print (os.path.abspath(base_dir))
        folder_name = folder_name.replace('../','').replace('./','').replace('/','') #FIXME Resolve for Windows and find a better way for replacing

        hash_data = {folder_name:{}}
        hash_data[folder_name].update({"folder_hash":self.set_folder_hash(os.path.relpath(base_dir))})
        hash_data[folder_name].update({"folder_dir":os.path.relpath(base_dir)})

        if verbose:
            print("FOLDER -->", os.path.relpath(base_dir))

        for item in os.listdir(base_dir):
            if os.path.isdir(base_dir+self.folder_separator+item):
                if en_recursive and not re.match(r"\.|__",item):
                    hash_data[folder_name].update(self.generate_hash(os.path.relpath(base_dir+self.folder_separator+item),verbose=verbose))
            else:
                if verbose:
                    print("FILE   -->", os.path.relpath(base_dir+self.folder_separator+item))
                hash_data[folder_name].update({item:self.set_file_hash(os.path.relpath(base_dir+self.folder_separator+item))})

        return hash_data

    #
    # GENERATE JSON
    #
    def set_tree_hash(self,base_dir=None,save_to_file="",verbose=False, file_to_json="", hash_data={}):
        super().set_tree_hash(save_to_file=save_to_file,verbose=verbose, file_to_json=file_to_json,hash_data=self.generate_hash(base_dir=base_dir,verbose=verbose))
        return self.json_hash


class HashChecker(Hash):
    def __init__(self,base_dir = None, get_tree_hash_en=True,hash_data={},file_to_json=""):
        super().__init__(base_dir)
        self.set_tree_hash(hash_data=hash_data,file_to_json=file_to_json)

        #--- VARS
        self.only_in_remote = []
        self.only_in_local  = []

    def __get_dictionary_to_compare(self,folder_name="",remote_dict={}):
        if not folder_name or not remote_dict:
            print ("FOLDER NAME OR REMOTE DICT NOT SET") #FXIME Make exception
            return

        for key in remote_dict.keys():
            if key == folder_name:
                return remote_dict[key]

        for key in remote_dict.keys():
            if isinstance(remote_dict[key],dict):
                result = self.__get_dictionary_to_compare(folder_name,remote_dict[key])
                if result: #If is different from 0
                    return result
            else:
                return 0

    def __compare_hash(self,local_dict,remote_dict):
        for key in local_dict.keys():
            if local_dict[key] == remote_dict[key]:
                return "SUCCESS",key,local_dict[key],remote_dict[key]
            elif not os.path.isdir(local_dict["file_dir"]):
                self.copy_file(local_dict["file_dir"],remote_dict['folder_dir'])
                return "CHANGE",key,local_dict[key],remote_dict[key]
            else:
                return "CHANGE",key,local_dict[key],remote_dict[key]

    def __compare_tree(self,base_dir="",remote_dict={}):
        if not base_dir or not remote_dict:
            print ("FOLDER NAME OR REMOTE DICT NOT SET") #FXIME Make exception
            return

        temp_dict  = {"folder_hash" : self.set_hash(os.path.relpath(base_dir)),
                       "file_dir"    : os.path.relpath(base_dir)
                     }

        if "CHANGE" in self.__compare_hash(temp_dict,remote_dict):
            for item in os.listdir(base_dir):
                if item in remote_dict.keys() and not re.match(r"\.|__",item):

                    if os.path.isdir(base_dir+self.folder_separator+item):
                        self.__compare_tree(os.path.relpath(base_dir+self.folder_separator+item),remote_dict[item])
                    else:
                        temp_dict  = {item      : self.set_hash(os.path.relpath(base_dir+self.folder_separator+item)),
                                      "file_dir": os.path.relpath(base_dir+self.folder_separator+item)
                                       }
                        print(self.__compare_hash(temp_dict,remote_dict))

                else:
                    if not re.match(r"\.|__",item):
                        self.copy_file(os.path.relpath(base_dir+self.folder_separator+item),remote_dict['folder_dir'])
            return "CHANGED"
        else:
            return "SUCCESS"

        # comparison_dict = {folder_name: {'only_in_remote':[],
        #                                  'only_in_local' :[],
        #                                  'both'          :[]
        #                                 }
        #                   }

        # remote_dir = set(remote_dict.keys()).remove("folder_hash").remove("folder_dir")
        # local_dir  = set(os.listdir(base_dir))

        # #----------------------------------------------- Determine files and folder names only in the remote
        # for name in remote_dir-local_dir:
        #     comparison_dict[folder_name]['only_in_remote'].append({"name": remote_dict['folder_dir']+self.folder_separator+name,
        #                                                            "hash": remote_dict[name]})

        # #----------------------------------------------- Determine files and folder names only in the local
        # for name  in local_dir-remote_dir:
        #     comparison_dict[folder_name]['only_in_local'].append({"name":               os.path.relpath(base_dir+self.folder_separator+name),
        #                                                           "hash": self.set_hash(os.path.relpath(base_dir+self.folder_separator+name))})

        # #----------------------------------------------- Check if folders_changed names

    def check_tree_hash(self,base_dir="",hash_data={},file_to_json=""):
        if not base_dir:
            base_dir = self.base_dir

        *base_name,folder_name = os.path.abspath(base_dir).split(self.folder_separator)
        folder_name = folder_name.replace('../','').replace('./','').replace('/','') #FIXME Resolve for Windows and find a better way for replacing

        if hash_data or file_to_json:
            self.set_tree_hash(hash_data=hash_data,file_to_json=file_to_json)

        #Find dir in dictionary
        remote_dict = self.__get_dictionary_to_compare(folder_name,self.hash_data)
        print(self.__compare_tree(os.path.relpath(base_dir),remote_dict))

        #Generar hash para nuevas carpetas
        #Copiar nuevo hash a los archivos modificados
        #Testar copy-paste
        #Agregar conexión remota
        #Crear main
        #Ver de hacer lista si hay nombres cambiados






