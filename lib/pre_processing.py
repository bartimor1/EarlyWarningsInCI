from collections import defaultdict
from dataclasses import make_dataclass
from datetime import datetime
import pandas as pd
import re, pm4py

record = make_dataclass("Record", [("timestamp", str),
                                   ("resource", str),
                                   # ("user", str),
                                   ("req_id", str),
                                   # ("tenant", str),
                                   # ("role", str),
                                   ("msg", str),
                                   ("pid", str),
                                   ("action", str),
                                   ("line", int),
                                  ]
                       )


def get_records(fh, previous_templates):
    # convert messages into templates, only if template doesn't
    # match the existing templates, we will create a new one.
    templates_to_records = defaultdict(list)
    changed_templates = set()
    used_templates = set()
    records = []
    num_of_None_req = 0
    for line in fh:
        regex_pattern = r'(\S+\s+\d+\s+\d+:\d+:\d+\.\d+).*?\[(\d+)\]:\s+[A-Z]+\s(\S+)\s*\[(\S*?)\s*?(req-\S+)?\s*?(\S*?)\s*?(\S*?)\]\s+(.+?)\s+{{\S+pid=\d+\)\s+(\S+).+?:(\d+)'
        regex_pattern2 = r'(\S+\s+\d+\s+\d+:\d+:\d+\.\d+).*?\[(\d+)\]:\s+[A-Z]+\s(\S+)\s*\[(\S*?)\s*?(req-\S+)?\s*?(\S*?)\s*?(\S*?)\]\s+(.+)'
        regex_pattern3 = r'(\S+\s+\d+\s+\d+:\d+:\d+\.\d+).*?\[(\d+)\]:(.+)'
        regex_sim_pattern = r'(\d+\.?\d*).+module=(\S+)\s+funcName=(\S+)\s+lineno=(\d+)\s+id=(\d+)\s+(.+)'

        sim_match = re.search(regex_sim_pattern, line)
        match = re.search(regex_pattern, line) or re.search(regex_pattern2, line)
        match2 = re.search(regex_pattern3, line)
        if sim_match:
            timestamp = float(sim_match.group(1))
            pid = 1
            msg = sim_match.group(6)
            module = sim_match.group(2)
            req_id = sim_match.group(5)
            function = sim_match.group(3)
            line_num = sim_match.group(4)

        elif match:
            timestamp = match.group(1)
            pid = str(match.group(2))
            module = match.group(3)
            req_id = match.group(5) if match.group(5) and len(match.groups()) >= 5 and match.group(5).startswith(
                "req-") else 'service_general'
            msg = match.group(8) if len(match.groups()) >= 8 and match.group(8) not in ['-', ''] else 'None'
            function = match.group(9) if len(match.groups()) >= 9 and match.group(9) not in ['-', ''] else 'None'
            line_num = match.group(10) if len(match.groups()) >= 10 and match.group(10) not in ['-', ''] else 'None'

        elif match2:
            timestamp = match2.group(1)
            pid = str(match2.group(2))
            msg = match2.group(3)
            module = 'None'
            req_id = 'process_general'
            function = 'None'
            line_num = 'None'
        else:
            print(f"line did not match regex:\n {line_num}\n ")

        # count number of general messages:
        if req_id == 'None':
            num_of_None_req += 1

        if sim_match:
            current_date = datetime.now()

            # Extract the current day and month
            hours = int(timestamp // 3600)
            minutes = int((timestamp % 3600) // 60)
            seconds = (timestamp % 3600)  % 60

            day = current_date.day
            month = current_date.month
            year = current_date.year  # need to explain it
            time = f'{hours}:{minutes}:{seconds:.5f}'
            timestamp_str = f"{year}-{month}-{day} {time}"
        else:

            year = datetime.now().year  # need to explain it
            month, day, time = timestamp.split(' ')
            month_number = datetime.strptime(month, '%b').month
            timestamp_str = f"{year}-{month_number}-{day} {time}"

            msg = re.sub(r'^[a-z_]+\s+=.*', 'log option value', msg)
            msg = re.sub(r'^[a-z_\.0-9]+\s+=.*', 'glance store log option value', msg)
            msg = re.sub(r'Determining version of request:.+', 'Determining version of request', msg)
            msg = re.sub(r'new path \/.+', 'new path **', msg)
            msg = re.sub(r'Acquiring lock \".+\" by \".+\"', 'Acquiring lock ** by **', msg)
            msg = re.sub(r'Lock \".+\" acquired by \".+', 'Lock ** acquired by **', msg)
            msg = re.sub(r'Lock \".+\" \"released\" by \".+', 'Lock ** released by **', msg)
            msg = re.sub(r'Task \'.+\'\s+\(.+\) transitioned into state \'[A-Z]+\' from state \'[A-Z]+\' with result.+',
                         'Task transitioned states', msg)
            msg = re.sub(r'Task \'.+\'\s+\(.+\) transitioned into state \'[A-Z]+\' from state \'[A-Z]+\'',
                         'Task transitioned states without results', msg)
            msg = re.sub(r'Flow \'.+\'\s+\(.+\) transitioned into state \'[A-Z]+\' from state \'[A-Z]+\'',
                         'Flow transitioned state', msg)
            msg = re.sub(r'Image .+ status changing from [a-z]+ to [a-z]+', 'Image status changed', msg)
            msg = re.sub(r'Writing DB stats.+', 'Writing DB stats', msg)
            msg = re.sub(r'REQ:.+ -i https:.+', 'REQ -i ***', msg)
            msg = re.sub(r'RESP BODY:.+\[.*', 'RESP BODY:**', msg)
            msg = re.sub(r'\{\"token\": \{\"methods\": \[\"password\"\], \"user\": \{\"domain\": \{\"id\":.+',
                         'get auth ref', msg)
            msg = re.sub(r'Image [a-zA-Z0-9-]+\s+[a-z_]+=', 'Image log option', msg)
            msg = re.sub(r'No image found with ID.+', 'No image found with ID **', msg)
            msg = re.sub(r'Wrote chunk.+\(\d\/\?\) of length.+to [a-zA-Z\._]+ returning MD5 of content:.+', 'wrote chunk',
                         msg)
            msg = re.sub(r'The metadata definition object with name=.+ was not found in namespace=.+',
                         'object metadata was not found', msg)
            msg = re.sub(r'Metadata definition namespace=.+ was not found.+', 'Metadata definition was not found', msg)
            msg = re.sub(r'User not permitted to delete metadata namespace \'.+\'', 'User not permitted fot operation', msg)
            msg = re.sub(r'User not permitted to \w+ metadata namespace \'.+\'', 'User not permitted fot operation', msg)
            msg = re.sub(r'No image found with ID .+', 'No image found for ID', msg)
            msg = re.sub(r'hit limit for project: \[Resource.+', 'hit limit', msg)
            msg = re.sub(r'Skipping [a-z_\.]+ not implemented.', 'not implemented', msg)
            msg = re.sub(r'After upload to the backend, deleting staged image data from .+', 'deleting staged image data',
                         msg)
            msg = re.sub(r'Enabling in-flight format inspection for .+', 'Enabling in-flight format inspection', msg)
            msg = re.sub(r'Spawning with ThreadPoolExecutor: .+', 'Spawning with ThreadPoolExecutor', msg)
            msg = re.sub(r'config files: \[.+\]', 'config files', msg)
            msg = re.sub(r'Creating threadpool model \'ThreadPoolExecutor\' with size \d+', 'Creating threadpool model',
                         msg)
            msg = re.sub(r'RESP HEADERS:.+', 'RESP HEADERS', msg)
            msg = re.sub(r'RESP STATUS:.+', 'RESP STATUS', msg)
            msg = re.sub(r'Failed to find image .+ to delete:.+.common.exception.ImageNotFound:.+image found for ID',
                         'Image not found exception', msg)
            msg = re.sub(
                r'Staged image data not found at .+.common.exception.LimitExceeded:.+ request returned a \d+ Request Entity Too Large. This generally means that rate limiting or a quota threshold was breached.',
                'Staged image data not found', msg)
            msg = re.sub(r'Deprecated:.+from group.+', "Deprication msg", msg)
            msg = re.sub(r'The request returned a \d+ Request Entity Too Large.+', 'Entity Too Large', msg)

            msg = re.sub(r'(\/\S+\)?){1,10}', '<path>', msg)
            msg = re.sub(r'(\s\/\s){1,10}', ' <path> ', msg)
            msg = re.sub(r'[0-9a-fA-F]+(?:-[0-9a-fA-F]+){1,8}', '****', msg)
            msg = re.sub(r'/v_num/.+?\?\w+=[a-zA-Z0-0-]+\s+?=>', r'\/v_num\/attr=** =>', msg)
            msg = re.sub(r'/\w+ => generated', r'\/attr=** => generated', msg)
            msg = re.sub(r'\w+-\w+-\w+-\w+-\w+[-0-9a-z]*', '**', msg)
            msg = re.sub(r'=\s*\w+', '= **', msg)
            msg = re.sub(r'0x\w+', '0x*******', msg)
            msg = re.sub(r':\s*\w+', ':*****', msg)
            msg = re.sub(r'\'Date\':\s*\'.+\'', 'Date:***', msg)
            msg = re.sub(r'AUTH_\w+', 'AUTH_*****', msg)
            msg = re.sub(r'[\"\']?id[\"\']:\s*[\"\'][a-z0-9-]+[\"\']', '\"id\": ****', msg)
            msg = re.sub(r'\/v\d+\/\w+', '/v_num/****', msg)
            msg = re.sub(r'expires_at\":\s*\"[0-9a-zA-Z-]+\"', 'expires_at": ****', msg)
            msg = re.sub(r'issued_at\":\s*\"[0-9a-zA-Z-]+', 'issued_at": ****', msg)
            msg = re.sub(r'Attempting to import store [a-zA-Z0-9\._]+', 'Attempting to import store', msg)
            msg = re.sub(r'Registering scheme [\w+]+ with.+', 'Registering scheme **', msg)
            msg = re.sub(r'Store [\w_\.]+ doesn\'t support updating dynamic storage capabilities',
                         'Store ** doesn\'t support updating dynamic storage capabilities', msg)
            msg = re.sub(r'Registering store [a-zA-z\.]+ with schemes.+', 'Registering store ** with schemes', msg)
            msg = re.sub(r'Late loading location class .+', 'Late loading location class **', msg)
            msg = re.sub(r'\(\d\/?\)', '(*/?)', msg)
            msg = re.sub(r'(\d*\w+\d+\w*){2,30}', '**', msg)
            msg = re.sub(r'\d+', '**', msg)
            msg = re.sub(r'Sun|Mon|Tue|Wed|Thu|Fri|Sat', 'Day', msg)
            msg = re.sub(r'Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec', 'Month', msg)
            msg = re.sub(r'\s+', ' ', msg)

        for template in previous_templates:
            # same template
            template_set = set(template)
            if {module, function, line_num, msg}.issubset(template_set):
                msg_template = template[4]
                used_templates.add(template)
                break

            # same module, function, line number, but different message
            if {module, function, line_num}.issubset(template_set) and not {'None', 'None', 'None'}.issubset(
                    template_set):
                msg_template = template[4]
                changed_templates.add(msg_template)
                used_templates.add(template)
                break

            # same module, function, msg, but different line
            if {module, function, msg}.issubset(template_set):
                # case were there is a same msg in several templates
                ### Limitation: we will search if there is another one with a correct line
                ### But may fail classifying the template if we have 2 templates with same msg with different lines in code
                ### and both line numbers were changed in the suggested revision
                for tmp_template in list(previous_templates):
                    if {module, function, line_num, msg}.issubset(set(tmp_template)):
                        msg_template = tmp_template[4]
                        used_templates.add(tmp_template)
                        break
                else:
                    msg_template = template[4]
                    used_templates.add(template)
                break

        else:
            for template in used_templates:
                if {module, function, line_num, msg}.issubset(set(template)):
                    msg_template = template[4]
                    break
            else:
                total_templates = set(previous_templates)
                total_templates.update(used_templates)
                total_templates.update(changed_templates)
                msg_template = f"temp_{len(total_templates)}"  # _{suffix}"
                template = (module, function, line_num, msg, msg_template)
                used_templates.add(template)
        templates_to_records[msg_template].append(line)

        # records.append(record(timestamp_str, module, user, req_id, tenant, role, msg_template, pid, function, line_num))
        records.append(record(timestamp_str, module, req_id, msg_template, pid, function, line_num))

    return records, used_templates, changed_templates, templates_to_records
