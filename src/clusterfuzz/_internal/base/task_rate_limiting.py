# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Task rate limiting."""

import datetime

from clusterfuzz._internal.datastore import data_types
from clusterfuzz._internal.datastore import ndb_utils
from clusterfuzz._internal.metrics import logs


def _get_datetime_now():
  return datetime.datetime.now()


class TaskRateLimiter:
  """Rate limiter for tasks."""
  TASK_RATE_LIMIT_WINDOW = datetime.timedelta(hours=6)
  TASK_RATE_LIMIT_MAX_ERRORS = 100
  TASK_RATE_LIMIT_MAX_COMPLETIONS = 2000

  def __init__(self, task_name, task_argument, job_name):
    self.task_name = task_name
    self.task_argument = task_argument
    self.job_name = job_name

  @property
  def readable_name(self):
    return ' '.join([self.task_name, self.task_argument, self.job_name])

  def record_task(self, success: bool) -> None:
    """Records a task and whether it completed succesfully."""
    if self.task_name in {'uworker_main', 'postprocess', 'preprocess'}:
      # Don't rate limit these fake uworker tasks.
      return
    if success:
      status = data_types.TaskState.FINISHED
    else:
      status = data_types.TaskState.ERROR
    window_task = data_types.WindowRateLimitTask(
        task_name=self.task_name,
        task_argument=self.task_argument,
        job_name=self.job_name,
        status=status)
    window_task.put()

  def is_rate_limited(self) -> bool:
    """Checks if the given task is rate limited."""
    if self.task_name in {'uworker_main', 'postprocess', 'preprocess'}:
      # Don't rate limit these fake tasks.
      return False
    if environment.get_value('COMMAND_OVERRIDE'):
      # A user wants to run this task.
      return False
    window_start = _get_datetime_now() - self.TASK_RATE_LIMIT_WINDOW
    query = data_types.WindowRateLimitTask.query(
        data_types.WindowRateLimitTask.task_name == self.task_name,
        data_types.WindowRateLimitTask.task_argument == self.task_argument,
        data_types.WindowRateLimitTask.job_name == self.job_name,
        data_types.WindowRateLimitTask.timestamp >= window_start)
    tasks = ndb_utils.get_all_from_query(query)
    completed_count = 0
    error_count = 0
    for task in tasks:
      # Limit based on completions.
      completed_count += 1
      if completed_count > self.TASK_RATE_LIMIT_MAX_COMPLETIONS:
        logs.warning(
            f'{self.readable_name} rate limited. '
            f'It ran at least {self.TASK_RATE_LIMIT_MAX_COMPLETIONS} in window.'
        )
        return True

      # Limit based on errors.
      if task.status == data_types.TaskState.ERROR:
        error_count += 1
      if error_count > self.TASK_RATE_LIMIT_MAX_ERRORS:
        logs.warning(
            f'{self.readable_name} rate limited. '
            f'It errored at least {self.TASK_RATE_LIMIT_MAX_ERRORS} in window.')
        return True

    return False