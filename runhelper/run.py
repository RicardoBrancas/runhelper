import csv
import multiprocessing
import os.path
import pathlib
import re
import subprocess
from typing import Callable

from ordered_set import OrderedSet


def run(instance_id, base_command, command, output_file):
    pathlib.Path(os.path.dirname(output_file)).mkdir(parents=True, exist_ok=True)
    command = base_command + ['-o', output_file] + command
    print(' '.join(command))
    p = subprocess.run(command, capture_output=True, encoding='utf8')

    instance_data = {'instance': instance_id,
                     'real': float(re.search('Real time \(s\): (.*)', p.stdout)[1]),
                     'cpu': float(re.search('CPU time \(s\): (.*)', p.stdout)[1]),
                     'ram': int(re.search('Max. memory \(cumulated for all children\) \(KiB\): (.*)', p.stdout)[1]),
                     'timeout': re.search('Maximum wall clock time exceeded: sending SIGTERM then SIGKILL', p.stdout) is not None,
                     'memout': re.search('Maximum memory exceeded: sending SIGTERM then SIGKILL', p.stdout) is not None}

    try:
        instance_data['status'] = re.search('Child status: (.*)', p.stdout)[1]
    except:
        instance_data['status'] = None if instance_data['timeout'] or instance_data['memout'] else 0

    if os.path.isfile(output_file):
        with open(output_file) as f:
            log = f.read()
            for tag, value in re.findall(r'runhelper\.(.*)=(.*)', log):
                instance_data[tag] = value

    return instance_id, instance_data, output_file


class Runner:

    def __init__(self, runsolver_path: str, csv_out_file: str, timeout: int = None, memout: int = None, termination_wait_time: int = 5, pool_size: int = 1):
        if os.path.isfile(runsolver_path):
            self.runsolver_path = runsolver_path
        else:
            raise FileNotFoundError('Path to runsolver is invalid.')

        self.csv_out_file = csv_out_file

        self.timeout = timeout
        self.memout = memout
        self.termination_wait_time = termination_wait_time

        self.base_command = [self.runsolver_path, '-d', str(self.termination_wait_time)]
        if timeout is not None:
            self.base_command += ['-W', str(self.timeout)]
        if memout is not None:
            self.base_command += ['--rss-swap-limit', str(self.memout)]

        self.pool = multiprocessing.Pool(pool_size)
        self.async_results = []
        self.instance_callback = None
        self.columns = OrderedSet()
        self.rows = []

    def register_instance_callback(self, callback: Callable[[str, dict, str], None]):
        """Register a callback to be called after each instance finishes running.
           The callback will be called with (instance_id, instance_data, output_file_path)
           Additions/modifications to the instance_data dictionary will be stored in the CSV file"""
        self.instance_callback = callback

    def _process(self, result):
        instance_id, instance_data, output_file = result
        if self.instance_callback:
            self.instance_callback(instance_id, instance_data, output_file)

        if not all(map(lambda k: k in self.columns, instance_data.keys())):
            print('New tag found. Re-printing data.')
            for key in instance_data.keys():
                if key not in self.columns:
                    self.columns.add(key)

            with open(self.csv_out_file + '_', 'w') as f:
                writer = csv.writer(f)
                writer.writerow(self.columns)
                writer.writerows(self.rows)

            os.remove(self.csv_out_file)
            os.rename(self.csv_out_file + '_', self.csv_out_file)

        row = tuple(instance_data.get(key, None) for key in self.columns)
        self.rows.append(row)

        with open(self.csv_out_file, 'a') as f:
            writer = csv.writer(f)
            writer.writerow(row)
            f.flush()

    def schedule(self, instance_id, args, output_file):
        """Schedule an instance for running when there are processes available in the pool"""
        result = self.pool.apply_async(run, (instance_id, self.base_command, args, output_file), callback=self._process)
        self.async_results.append(result)

    def wait(self):
        """Wait for all the currently scheduled instances to finish executing"""
        for result in self.async_results:
            result.wait()
