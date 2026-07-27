from __future__ import annotations

import uuid

from PySide6.QtCore import QObject, Signal

from pandoc_gui.command import PandocCommandBuilder, command_preview
from pandoc_gui.models import ConversionJob, JobState
from pandoc_gui.runner import PandocRunner


class JobQueue(QObject):
    job_added = Signal(object)
    job_updated = Signal(object)
    log_received = Signal(str)
    queue_idle = Signal()

    def __init__(self, builder: PandocCommandBuilder, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.builder = builder
        self.jobs: list[ConversionJob] = []
        self.runner = PandocRunner(self)
        self.runner.started.connect(self._job_started)
        self.runner.finished.connect(self._job_finished)
        self.runner.output_received.connect(self._output_received)

    def set_builder(self, builder: PandocCommandBuilder) -> None:
        if self.runner.running:
            raise RuntimeError("任务运行时不能切换 Pandoc。")
        self.builder = builder

    def enqueue(self, job: ConversionJob) -> None:
        if not job.identifier:
            job.identifier = uuid.uuid4().hex
        self.builder.validate(job)
        job.state = JobState.WAITING
        self.jobs.append(job)
        self.job_added.emit(job)
        self._start_next()

    def retry(self, identifier: str) -> None:
        job = self.find(identifier)
        if not job or job.state not in {JobState.FAILED, JobState.CANCELED}:
            return
        job.state = JobState.WAITING
        job.exit_code = None
        self.job_updated.emit(job)
        self._start_next()

    def remove(self, identifier: str) -> None:
        job = self.find(identifier)
        if not job or job.state == JobState.RUNNING:
            return
        self.jobs.remove(job)
        self.job_updated.emit(job)

    def cancel_active(self) -> None:
        self.runner.cancel()

    def clear_finished(self) -> None:
        self.jobs = [job for job in self.jobs if job.state in {JobState.WAITING, JobState.RUNNING}]
        self.job_updated.emit(None)

    def find(self, identifier: str) -> ConversionJob | None:
        return next((job for job in self.jobs if job.identifier == identifier), None)

    def _start_next(self) -> None:
        if self.runner.running or self.runner.current_job is not None:
            return
        job = next((item for item in self.jobs if item.state == JobState.WAITING), None)
        if not job:
            self.queue_idle.emit()
            return
        try:
            invocation = self.builder.build(job)
        except Exception as error:
            job.state = JobState.FAILED
            job.stderr = str(error)
            self.job_updated.emit(job)
            self._start_next()
            return
        self.log_received.emit(f"$ {command_preview(invocation)}\n")
        self.runner.run(job, invocation)

    def _job_started(self, job: ConversionJob) -> None:
        self.job_updated.emit(job)

    def _job_finished(self, job: ConversionJob) -> None:
        self.job_updated.emit(job)
        self._start_next()

    def _output_received(self, channel: str, text: str) -> None:
        prefix = "" if channel == "stdout" else "[stderr] "
        self.log_received.emit(f"{prefix}{text}")

