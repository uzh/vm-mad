
class SimSchedInfo(object):

    def __init__(self, workload_file):
        #self._workload = read(workload_file)
        self._step = 0

    def __call__(self):
        """Return pair of (running, pending) jobs."""
        self._step += 1
        return self._workload[self._step]


class OrchestratorSimulation(orchestrator.Orchestrator):

    def __init__(self, workload_filename, max_vms, max_delta=1):
        Orchestrator.__init__(self, max_vms, max_delta)
        self.sim_sched_info = SimSchedInfo(workload_filename)
        self._started_vms = 0 

    # override `_get_sched_info`
    def _get_sched_info(self):
        return self.sim_sched_info()

    def _start_vm(self):
        self._started_vms += 1

    def _stop_vm(self):
        self._started_vms -= 1
