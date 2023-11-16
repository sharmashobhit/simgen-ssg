import re
import os
from pathlib import Path

blacklist = ["^\.", "\.swp$"]
whitelist = ["\.md$", "\.txt$"]


def file_filter(name):
    def run_filters(name, filters):
        for regex in filters:
            if re.search(regex, name):
                return True
        return False

    if len(whitelist) > 0:
        return run_filters(name, whitelist)
    else:
        return not run_filters(name, blacklist)


def files_updated_since(path, last_mtime):
    req_path = Path(path)
    for top_level in [x for x in os.listdir(req_path) if not x.startswith(".")]:
        for root, dirs, files in os.walk(req_path.joinpath(top_level)):
            for file_name in filter(file_filter, files):
                if os.path.getmtime(os.path.join(root, file_name)) > last_mtime:
                    yield os.path.join(root, file_name)


# command_index = 1
# while sys.argv[command_index] == '-f':
#     file_rule = sys.argv[command_index + 1]
#     if file_rule.startswith('*'):
#         file_rule = file_rule[1:]
#     whitelist.append("%s$" %file_rule)
#     command_index += 2

# # We concatenate all of the arguments together, and treat that as the command to run
# command = ' '.join(sys.argv[command_index:])

# # The path to watch
# path = '.'

# # How often we check the filesystem for changes (in seconds)
# wait = 1

# # The process to autoreload
# process = subprocess.Popen(command, shell=True)

# # The current maximum file modified time under the watched directory
# last_mtime = max(file_times(path))

# while True:
#     max_mtime = max(file_times(path))
#     print_stdout(process)
#     if max_mtime > last_mtime:
#         last_mtime = max_mtime
#         if process.poll():
#             print 'Restarting process.'
#             process.kill()
#         else:
#             print 'No process to kill.'
#         process = subprocess.Popen(command, shell=True)
#     time.sleep(wait)
