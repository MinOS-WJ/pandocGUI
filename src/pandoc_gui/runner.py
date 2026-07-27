from __future__ import annotations

from PySide6.QtCore import QObject, QProcess, QTimer, Signal

from pandoc_gui.models import CommandInvocation, ConversionJob, JobState


class PandocRunner(QObject):
    output_received = Signal(str, str)
    finished = Signal(object)
    started = Signal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        self.process.readyReadStandardOutput.connect(self._read_stdout)
        self.process.readyReadStandardError.connect(self._read_stderr)
        self.process.started.connect(self._on_started)
        self.process.finished.connect(self._on_finished)
        self.process.errorOccurred.connect(self._on_error)
        self.current_job: ConversionJob | None = None
        self._cancel_requested = False
        self._invocation: CommandInvocation | None = None

    @property
    def running(self) -> bool:
        return self.process.state() != QProcess.ProcessState.NotRunning

    def run(self, job: ConversionJob, invocation: CommandInvocation) -> None:
        if self.running or self.current_job is not None:
            raise RuntimeError("PandocRunner 已在运行任务。")
        self.current_job = job
        self._invocation = invocation
        self._cancel_requested = False
        job.stdout = ""
        job.stderr = ""
        job.exit_code = None
        self.process.setWorkingDirectory(invocation.working_directory)
        self.process.start(invocation.executable, invocation.arguments)

    def cancel(self) -> None:
        if not self.running:
            return
        self._cancel_requested = True
        self.process.terminate()
        QTimer.singleShot(1500, self._force_kill)

    def _force_kill(self) -> None:
        if self.running:
            self.process.kill()

    def _read_stdout(self) -> None:
        text = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        if self.current_job:
            self.current_job.stdout += text
        if text:
            self.output_received.emit("stdout", text)

    def _read_stderr(self) -> None:
        text = bytes(self.process.readAllStandardError()).decode("utf-8", errors="replace")
        if self.current_job:
            self.current_job.stderr += text
        if text:
            self.output_received.emit("stderr", text)

    def _on_started(self) -> None:
        if self.current_job:
            self.current_job.state = JobState.RUNNING
            self.started.emit(self.current_job)

    def _on_finished(self, exit_code: int, _exit_status: QProcess.ExitStatus) -> None:
        self._read_stdout()
        self._read_stderr()
        job = self.current_job
        self.current_job = None
        self._invocation = None
        if not job:
            return
        job.exit_code = exit_code
        if self._cancel_requested:
            job.state = JobState.CANCELED
        elif exit_code == 0:
            job.state = JobState.SUCCEEDED
        else:
            job.state = JobState.FAILED
        self.finished.emit(job)

    def _on_error(self, error: QProcess.ProcessError) -> None:
        if error == QProcess.ProcessError.Crashed:
            return
        job = self.current_job
        if not job:
            return
        message = self.process.errorString()
        job.stderr += message
        job.exit_code = -1
        job.state = JobState.CANCELED if self._cancel_requested else JobState.FAILED
        self.current_job = None
        self._invocation = None
        self.output_received.emit("stderr", message)
        self.finished.emit(job)

