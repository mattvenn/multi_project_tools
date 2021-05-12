#!/usr/bin/env python3
import matplotlib.pyplot as plt

import os
import re
import datetime
caravel = '/home/matt/work/asic-workshop/shuttle2-mpw-two-b/caravel_user_project'
for config_number in range (1, 15):
    elapsed_times = []
    violations = []
    try:
        logfile = os.path.join(caravel, 'openlane', 'user_project_wrapper', 'tests', str(config_number), "19-tritonRoute.log")
        log = open(logfile)
        print(logfile)
        for line in log.readlines():
            m = re.search('number of violations = (\d+)', line)
            if m is not None:
                violations.append(int(m.group(1)))

            if len(violations):
                m = re.search('cpu time.*elapsed time = (\d+):(\d+):(\d+)', line)
                if m is not None:
                    elapsed_times.append(datetime.timedelta(hours=int(m.group(1)), minutes=int(m.group(2)), seconds=int(m.group(3))))
    except FileNotFoundError as e:
        break

    previous_time = datetime.timedelta()
    times = []
    iteration = 0
    for time, violation in zip(elapsed_times, violations):
        #print(iteration, previous_time, violation)
        times.append(previous_time.seconds)
        previous_time = time + previous_time
        iteration += 1

    plt.plot(times, violations, label=config_number, linewidth=3.0)

plt.xlabel('time')
plt.ylabel('violations')
plt.yscale('log')
plt.legend()
plt.grid()
plt.show()
