import os
import ast
import json
import pickle
import shutil


def read_json(filename):
    with open(filename, 'r') as f:
        data = json.load(f)
    return data


def write_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def write_pkl(filenane, data):
    with open(filenane, 'wb') as f:
        pickle.dump(data, f)


def read_pkl(filename):
    with open(filename, 'rb') as f:
        loaded_dict = pickle.load(f)
    return loaded_dict


def read_dev_logfile(filename):
    logs = []
    with open(filename, 'r') as f:
        for line in f.readlines():
            logs.append(ast.literal_eval(line.strip()))
    return logs


def res2tuple(res, debug=False):
    res = str(res).replace('(', '')
    res = str(res).replace(')', '')
    res = ast.literal_eval(res)
    if isinstance(res, dict):
        res = (res, )
    if debug:
        print(type(res))
        print(res)
    return res


def get_func_name(data):
    if isinstance(data, list):
        return data[0]
    elif isinstance(data, dict):
        return list(data.keys())[0]
    else:
        return data


def fix_map(nodes, edges):
    nodes_ = {}
    for n in nodes:
        if n[0] not in nodes_:
            nodes_[n[0]] = n[1]
        else:
            if n[1] == 0:
                nodes_[n[0]] = 0
    nodes_ = [[k, v] for k, v in nodes_.items()]
    nodes_[0][1] = 2
    edges_ = []
    count = {}
    for e in edges:
        t = '-'.join([e[0], e[1]])
        if t not in count:
            count[t] = [e[2], 1]
        else:
            if e[2] == 0:
                count[t][0] = 0
            count[t][1] += 1
    edges_ = [k.split('-') + v for k, v in count.items()]
    return nodes_, edges_


def delete_files(folder_path):
    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)
        if os.path.isfile(item_path):
            os.remove(item_path)
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)
