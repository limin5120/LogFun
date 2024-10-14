import os
import gzip
import shutil
import matplotlib
from .utils import *
import networkx as nx
import matplotlib.pyplot as plt


class LogManager():
    def __init__(self, template_file, output='./manager_output/'):
        if os.path.exists(template_file):
            self.data = read_pkl(template_file)
            self.filenames = self.data['_FILENAMES']
            self.filenames_r = {v: k for k, v in self.filenames.items()}
            self.templates = self.data['_TEMPLATES']
            self.templates_r = {v: k for k, v in self.templates.items()}
        self.path = template_file
        self.output = output
        os.makedirs(self.output, exist_ok=True)

    def _split_func(self, funcs):
        points = []
        t_ = 0
        t = funcs[t_]
        flag = False
        for i in range(len(funcs) - 1):
            if flag:
                flag = False
                continue
            if t == funcs[i + 1]:
                points.append([t_, i + 1])
                if i + 3 > len(funcs):
                    break
                t_ = i + 2
                t = funcs[i + 2]
                flag = True
        res = []
        for m, n in points:
            res.append(funcs[m:n + 1])
        return res

    def _parse_func(self, stacks, debug=False):
        if stacks[0] == stacks[1] and len(stacks) == 2:
            return [stacks[0]]
        else:
            res = self._split_func(stacks)
            if len(res) > 1:
                if debug:
                    print("----parallel Function split----")
                    for idx, i in enumerate(res):
                        print("functions", [idx], ":", i)
                content = ()
                for idx, r in enumerate(res):
                    if len(r) > 2:
                        if r[0] == r[-1] and len(r[1:-1]) > 1:
                            # single functions contain subfunction
                            content_ = {r[0]: [self._parse_func(r[1:-1], debug)]}
                        else:
                            # parallel function
                            content_ = self._parse_func(r, debug)
                    elif r[0] == r[1]:
                        # single function
                        content_ = self._parse_func(r, debug)
                    if debug:
                        print([idx], "analyze:", r)
                        print([idx], "results:", content_)
                    content = content + (content_, )
                return content
            else:
                # single function
                return {stacks[0]: [self._parse_func(stacks[1:-1], debug)]}

    def _build_map(self, funcs, debug=False):
        nodes = []
        edges = []
        for idx, f in enumerate(funcs):
            if debug:
                print("----process----", f)
            if idx + 1 < len(funcs):
                edges.append([get_func_name(f), get_func_name(funcs[idx + 1]), 1])
            if isinstance(f, list):
                if debug:
                    print("[3] add func node", f[0])
                nodes.append([f[0], 1])
            else:
                tmp_key = list(f.keys())[0]
                nodes.append([tmp_key, 0])
                if len(f[tmp_key]) < 2:
                    # single node
                    sub_node = f[tmp_key][0]
                    if isinstance(sub_node, dict):
                        if debug:
                            print("[1] single dict", sub_node)
                        edges.append([tmp_key, get_func_name(sub_node), 0])
                        nodes_, edges_ = self._build_map([sub_node], debug)
                        nodes += nodes_
                        edges += edges_
                        if debug:
                            print("[1] single dict res:", "node:", nodes_, "edge:", edges_)
                    elif isinstance(sub_node, list):
                        if debug:
                            print("[2] single list", sub_node)
                        edges.append([tmp_key, sub_node[0], 0])
                        nodes_, edges_ = self._build_map([[n] for n in sub_node], debug)
                        nodes += nodes_
                        edges += edges_
                        if debug:
                            print("[2] single list res:", "node:", nodes_, "edge:", edges_)
                else:
                    # Mult nodes
                    if debug:
                        print("[4] Multi nodes", f[tmp_key])
                    edges.append([tmp_key, get_func_name(f[tmp_key][0]), 0])
                    nodes_, edges_ = self._build_map(f[tmp_key], debug)
                    nodes += nodes_
                    edges += edges_
                    if debug:
                        print("[4] Multi node res:", "node:", nodes_, "edge:", edges_)
        return nodes, edges

    def _figure_map(self, nodes, edges):
        graph = nx.DiGraph()
        matplotlib.use("TkAgg")
        plt.figure(figsize=(20, 20), dpi=100)
        for n in nodes:
            if n[1] == 0:
                graph.add_node(n[0], color='green')
            elif n[1] == 1:
                graph.add_node(n[0], color='blue')
            else:
                graph.add_node(n[0], color='red')
        for e in edges:
            if e[2] == 0:
                graph.add_edge(e[0], e[1], color='lightgreen', weight=e[3])
            elif e[2] == 1:
                graph.add_edge(e[0], e[1], color='lightblue', weight=e[3])
        node_colors = [node[1]['color'] for node in graph.nodes(data=True)]
        edge_colors = [graph[u][v]['color'] for u, v in graph.edges()]
        pos = nx.shell_layout(graph, scale=10)  # shell_layout, circular_layout, spring_layout
        nx.draw(
            graph,
            pos,
            arrowstyle='->',
            arrowsize=100,
            node_size=3000,
            node_color=node_colors,
            edge_color=edge_colors,
            width=10,
        )
        edge_labels = nx.get_edge_attributes(graph, 'weight')
        label_pos = {k: v + [0.2, 0.8] for k, v in pos.items()}
        nx.draw_networkx_labels(graph, label_pos, font_size=32, font_weight='bold')
        nx.draw_networkx_edge_labels(graph, pos, edge_labels=edge_labels, font_size=40)
        plt.savefig(self.output + "funcs_callmap.png")
        return graph

    def run_parse_templates(self):
        if not os.path.exists(self.path):
            return
        sequence = self.data.copy()
        r_list = ['_STACK', '_TEMPLATES', '_FILENAMES']
        for r in r_list:
            sequence.pop(r, None)
        write_json(self.output + 'templates.json', self.templates)
        write_json(self.output + 'filenames.json', self.filenames)
        write_json(self.output + 'sequences.json', sequence)

    def run_parse_stacks(self, debug=False):
        if debug:
            print('---------------parse------------------')
        res = self._parse_func(self.data['_STACK'], debug)
        funcs = res2tuple(res, debug)
        if debug:
            print('---------------mapping------------------')
        nodes, edges = self._build_map(funcs, debug)
        nodes, edges = fix_map(nodes, edges)
        if debug:
            print("nodes:", nodes)
            print("edges:", edges)
        if debug:
            print('---------------figure------------------')
        self._figure_map(nodes, edges)
        return funcs, nodes, edges

    def config_filter(self, ids):
        filters = read_json(self.output + 'templates.json')
        config = {k: v for k, v in filters.items() if v in ids}
        path = os.path.dirname(self.path)
        write_pkl(path + '/templates_config.pkl', config)

    def clear_log_files(self, mode=False):
        path = os.path.dirname(self.path)
        # if os.path.exists(path):
        if mode:
            shutil.rmtree(path)
        else:
            delete_files(path)

    def clear_mgr_files(self, mode=False):
        # if os.path.exists(self.output):
        if mode:
            shutil.rmtree(self.output)
        else:
            delete_files(self.output)

    def _trans_dev2log_filter(self, line, s, filter_template, filter_filename, params=None):
        pid = line[0]
        func = self.filenames_r[line[1]] + ' ' + str(line[4])
        beginTime = line[2][0]
        endTime = line[2][-1]
        times = line[2]
        template = line[3]
        begin = line[5]
        context = line[6]
        end = line[7]
        if line[1] in filter_filename:
            tmp = ("%s %s %s Input %s\n") % (beginTime, pid, func, begin)
            if params:
                for i in set(tmp.split()):
                    for j in params:
                        if str(j) in i:
                            s.write(tmp)
                            break
            else:
                s.write(tmp)
        step = 1
        for idx in range(len(template)):
            if template[idx] in filter_template:
                c = self.templates_r[template[idx]] % context[idx] if context[idx] else self.templates_r[template[idx]]
                tmp = ("%s %s %s Step %s %s\n") % (times[idx + 1] + beginTime, pid, func, step, c)
                if params:
                    for i in set(tmp.split()):
                        for j in params:
                            if str(j) in i:
                                s.write(tmp)
                                break
                else:
                    s.write(tmp)
                step += 1
        if line[1] in filter_filename:
            tmp = ("%s %s %s Return %s\n") % (endTime + beginTime, pid, func, end)
            if params:
                for i in set(tmp.split()):
                    for j in params:
                        if str(j) in i:
                            s.write(tmp)
                            break
            else:
                s.write(tmp)

    def _trans_dev2log(self, line, s):
        pid = line[0]
        func = self.filenames_r[line[1]] + ' ' + str(line[4])
        beginTime = line[2][0]
        endTime = line[2][-1]
        times = line[2]
        template = line[3]
        begin = line[5]
        context = line[6]
        end = line[7]
        s.write(("%s %s %s Input %s\n") % (beginTime, pid, func, begin))
        step = 1
        for idx in range(len(template)):
            c = self.templates_r[template[idx]] % context[idx] if context[idx] else self.templates_r[template[idx]]
            s.write(("%s %s %s Step %s %s\n") % (times[idx + 1] + beginTime, pid, func, step, c))
            step += 1
        s.write(("%s %s %s Return %s\n") % (endTime + beginTime, pid, func, end))

    def search_dev_log(self, logfile, **keywords):
        keys = keywords.get('keys', None)
        params = keywords.get('params', None)
        search_file = keywords.get('output', 'search.log')
        logs = read_dev_logfile(logfile)
        filter_template = []
        filter_filename = []
        if keys:
            for t, v in self.templates.items():
                for i in set(t.split()):
                    for j in keys:
                        if j.upper() in i.upper():
                            filter_template.append(v)
                            break
            for t, v in self.filenames.items():
                for i in set(t.split()):
                    for j in keys:
                        if j.upper() in i.upper():
                            filter_filename.append(v)
            if params:
                with open(search_file, 'w') as s:
                    for line in logs:
                        line = self._trans_dev2log_filter(line, s, filter_template, filter_filename, params)
            else:
                with open(search_file, 'w') as s:
                    for line in logs:
                        line = self._trans_dev2log_filter(line, s, filter_template, filter_filename)
        else:
            with open(search_file, 'w') as s:
                for line in logs:
                    line = self._trans_dev2log(line, s)
        # print(logs)
