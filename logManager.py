from LogFun import LogManager

logm = LogManager('./logfun_output/trace.pkl')

logm.run_parse_templates()
logm.config_filter([1, 2, 3])

logm.run_parse_stacks()

logm.search_dev_log('dev.log', keys=["successfully"], params=[], output='search.log')
logm.search_dev_log('dev.log', output='dev_trans.log')

# logm.clear_log_files(mode=True)
# logm.clear_mgr_files(mode=True)
