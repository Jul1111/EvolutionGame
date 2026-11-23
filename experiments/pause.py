"""Pause or resume the running experiments (and their worker processes), without losing anything.

    python -m experiments.pause            pause every running experiment (they stop using the CPU)
    python -m experiments.pause reprise    resume them where they were
    python -m experiments.pause etat       list them, running or paused

A paused run keeps its memory and resumes exactly where it stopped (SIGSTOP / SIGCONT): the results are the same as
without a pause. It does not survive a shutdown or a reboot of the computer: a run interrupted that way is lost (the
seeds already finished are kept on disk). macOS and Linux only.
"""
import os
import signal
import subprocess
import sys

MODULES = ("experiments.lot", "experiments.run", "experiments.jardin", "experiments.gradient")


def processes():
    """{pid: (parent pid, state, command)} of every process of the user."""
    out = subprocess.check_output(["ps", "-o", "pid=,ppid=,state=,command=", "-u", str(os.getuid())], text=True)
    table = {}
    for line in out.splitlines():
        pid, ppid, state, command = line.split(None, 3)
        table[int(pid)] = (int(ppid), state, command)
    return table


def experiments(table=None):
    """Pids of the running experiments and of all their descendants (the workers of each seed), roots first."""
    table = processes() if table is None else table
    roots = [pid for pid, (_, _, cmd) in table.items() if pid != os.getpid()
             and any(f"-m {m}" in cmd or f"{m.replace('.', '/')}.py" in cmd for m in MODULES)]
    found, todo = [], list(roots)
    while todo:
        pid = todo.pop(0)
        if pid not in found:
            found.append(pid)
            todo += [p for p, (ppid, _, _) in table.items() if ppid == pid]
    return found


def main(argv=None):
    action = (argv if argv is not None else sys.argv[1:] or ["pause"])[0]
    if action not in ("pause", "reprise", "etat"):
        raise SystemExit(__doc__)
    table = processes()
    pids = experiments(table)
    if not pids:
        print("Aucune expérience en cours.")
        return
    if action == "etat":
        for pid in pids:
            _, state, cmd = table[pid]
            print(f"{pid:7d}  {'en pause' if state.startswith('T') else 'tourne  '}  {cmd[:100]}")
        return
    sig = signal.SIGSTOP if action == "pause" else signal.SIGCONT
    for pid in (pids if action == "pause" else reversed(pids)):   # Workers resume before their parent
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            pass
    print(f"{len(pids)} processus {'en pause' if action == 'pause' else 'repris'}.")


if __name__ == "__main__":
    main()
