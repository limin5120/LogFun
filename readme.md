### LogFun demo introduction

This is a simple demo that LogFun compared to logging in Python. The Python environments are listed in `requirements.txt`.

To run the demo:
```bash
# run logging demo 
Python demo_Logging.py
# run LogFun demo
Python demo_LogFun.py
# run LogManager demo
Python logManager.py
```
- Logging and LogFun demo will output the overhead of running time, and log files in `.log` and `.gz`.
- To compare the file size of them, you can just run `du -sh *.gz *.log`
- LogManager provide the demo of controlling, parsing templates, call relationships, decoding compressed logs and searching logs by keywords.

#### How to controlling log templates

This need to modify the code of `logManager.py` as follows:
```python
# when run logManager.py the templates are saved in manager_output
# [1, 2, 3] is the template id parsed by LogManager
logm.config_filter([1, 2, 3])
```
When change the code, you need to run `Python logManager.py` again to generate the config file for demo. Finally, run `Python demo_LogFun.py`, the log template will be filtered.