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
"""Holds helpers for reuse across different tasks."""


import datetime
import os
from clusterfuzz._internal.datastore import data_types
from clusterfuzz._internal.metrics import logs
from clusterfuzz._internal.metrics import monitoring_metrics
from typing import Optional


def emit_testcase_triage_duration_metric(testcase_id: int, step: str):
    testcase_upload_metadata = query_testcase_upload_metadata(testcase_id)
    if not testcase_upload_metadata:
       logs.error(f'No upload metadata found for testcase {testcase_id},'
                   ' failed to emit TESTCASE_UPLOAD_TRIAGE_DURATION metric.')
    if not testcase_upload_metadata.timestamp:
        logs.error(f'No timestamp for testcase {testcase_upload_metadata.testcase_id},'
                   ' failed to emit TESTCASE_UPLOAD_TRIAGE_DURATION metric.')
    assert step in [
        'analyze_launched', 'analyze_completed', 'minimize_completed',
        'regression_completed', 'impact_completed', 'issue_completed'
    ]
    elapsed_time_since_upload = datetime.datetime.utcnow()
    elapsed_time_since_upload -= testcase_upload_metadata.timestamp
    elapsed_time_since_upload = elapsed_time_since_upload.total_seconds()

    monitoring_metrics.TESTCASE_UPLOAD_TRIAGE_DURATION.add(
        elapsed_time_since_upload,
        labels = {
        'job': os.getenv('JOB_TYPE'),
        'step': step,
        }
    )


def query_testcase_upload_metadata(
    testcase_id: str) -> Optional[data_types.TestcaseUploadMetadata]:
  return data_types.TestcaseUploadMetadata.query(
      data_types.TestcaseUploadMetadata.testcase_id == int(testcase_id)).get()
