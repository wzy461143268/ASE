from itertools import product
from typing import Any, Callable, Dict, List
import pytest

from ase import Atoms
from ase.optimize.optimize import Dynamics


class DummyDynamics(Dynamics):
    def step(self):
        ...

    def log(self):
        print(f"Step {self.nsteps}")

    def converged(self):
        return False


@pytest.fixture(name="dynamics")
def fixture_dynamics(rattled_atoms: Atoms) -> Dynamics:
    return DummyDynamics(atoms=rattled_atoms)


class TestDynamics:
    @staticmethod
    @pytest.fixture(name="observer", scope="function")
    def fixture_observer() -> Dict[str, Any]:
        observer = {
            "function": print,
            "position": 0,
            "interval": 1,
        }
        return observer

    @staticmethod
    def test_should_return_zero_steps_after_instantiation(dynamics: Dynamics) -> None:
        assert dynamics.get_number_of_steps() == 0

    @staticmethod
    def test_should_insert_observer(
        observer: Dict[str, Any], dynamics: Dynamics
    ) -> None:
        dynamics.insert_observer(**observer)
        inserted_observer = dynamics.observers[observer["position"]]

        attributes_in_observer = []
        for k, v in observer.items():
            if k != "position":
                attributes_in_observer.append(v in inserted_observer)

        assert all(attributes_in_observer)

    @staticmethod
    def test_should_insert_observer_with_write_method_of_non_callable(
        dynamics: Dynamics, observer: Dict[str, Any]
    ) -> None:
        observer["function"] = dynamics.optimizable.atoms
        dynamics.insert_observer(**observer)
        assert dynamics.observers[0][0] == dynamics.optimizable.atoms.write

    @staticmethod
    def test_should_raise_not_implemented_error_when_calling_dynamics_todict(
        dynamics: Dynamics,
    ) -> None:
        with pytest.raises(NotImplementedError) as excinfo:
            _ = Dynamics.todict(dynamics)

        assert excinfo.type is NotImplementedError

    @staticmethod
    def test_should_raise_runtime_error_when_calling_dynamics_step(
        dynamics: Dynamics,
    ) -> None:
        with pytest.raises(RuntimeError):
            _ = Dynamics.step(dynamics)

    @staticmethod
    def test_should_attach_callback_function_if_callable_and_without_set_description() -> (
        None
    ):
        ...

    @staticmethod
    def test_should_call_set_description_if_callback_attached_has_set_description() -> (
        None
    ):
        ...

    @staticmethod
    def test_should_attach_write_method_if_function_not_callable() -> None:
        ...


class TestCallObservers:
    @staticmethod
    @pytest.fixture(name="insert_observers")
    def fixture_insert_observers(
        dynamics: Dynamics,
    ) -> Callable[[List[int]], None]:
        def _insert_observer(*, intervals: List[int]) -> None:
            for i, interval in enumerate(intervals):
                observer = (print, i, interval, f"Observer {i}")
                dynamics.insert_observer(*observer)

        return _insert_observer

    @staticmethod
    def test_should_call_inserted_observers(
        dynamics: Dynamics,
        capsys: pytest.CaptureFixture,
        insert_observers: Callable[[List[int]], None],
    ) -> None:
        insert_observers(intervals=[1])
        dynamics.call_observers()
        output: str = capsys.readouterr().out
        lines = output.splitlines()
        observer_outputs_present = []
        for i, _ in enumerate(dynamics.observers):
            observer_outputs_present.append(f"Observer {i}" in lines[i])
        assert all(observer_outputs_present)

    @staticmethod
    @pytest.mark.parametrize(
        "interval,step", [(i, i * j) for i, j in product([1, 2], repeat=2)]
    )
    def test_should_call_observer_every_positive_interval(
        dynamics: Dynamics,
        capsys: pytest.CaptureFixture,
        insert_observers: Callable[[List[int]], None],
        interval: int,
        step: int,
    ) -> None:
        insert_observers(intervals=[interval])
        dynamics.nsteps = step
        dynamics.call_observers()
        output: str = capsys.readouterr().out
        lines = output.splitlines()
        observer_outputs_present = []
        for i, _ in enumerate(dynamics.observers):
            observer_outputs_present.append(f"Observer {i}" in lines[i])
        assert all(observer_outputs_present)

    @staticmethod
    @pytest.mark.parametrize(
        "interval,step", [(i, i * j + 1) for i, j in product([-1, 2, 3], [1, 2])]
    )
    def test_should_not_call_observer_if_not_specified_interval(
        dynamics: Dynamics,
        capsys: pytest.CaptureFixture,
        insert_observers: Callable[[List[int]], None],
        interval: int,
        step: int,
    ) -> None:
        insert_observers(intervals=[interval])
        dynamics.nsteps = step
        dynamics.call_observers()
        output: str = capsys.readouterr().out
        lines = output.splitlines()
        observer_outputs_present = []
        for i, _ in enumerate(dynamics.observers):
            observer_outputs_present.append(
                all(f"Observer {i}" not in line for line in lines)
            )
        assert all(observer_outputs_present)

    @staticmethod
    @pytest.mark.parametrize("interval", (0, -1, -2, -3))
    def test_should_call_observer_on_specified_step_if_interval_negative(
        dynamics: Dynamics,
        capsys: pytest.CaptureFixture,
        insert_observers: Callable[[List[int]], None],
        interval: int,
    ) -> None:
        insert_observers(intervals=[interval])
        dynamics.nsteps = abs(interval)
        dynamics.call_observers()
        output: str = capsys.readouterr().out
        lines = output.splitlines()
        observer_outputs_present = []
        for i, _ in enumerate(dynamics.observers):
            observer_outputs_present.append(f"Observer {i}" in lines[i])
        assert all(observer_outputs_present)

    @staticmethod
    def test_should_call_observers_in_order_of_position_in_list(
        dynamics: Dynamics,
        capsys: pytest.CaptureFixture,
        insert_observers: Callable[[List[int]], None],
    ) -> None:
        insert_observers(intervals=[1] * 3)
        dynamics.call_observers()
        captured: str = capsys.readouterr().out
        messages_in_order = []
        for i, line in enumerate(captured.splitlines()):
            observer = dynamics.observers[i]
            args = observer[2]
            message = args[0]
            messages_in_order.append(line == message)

        assert all(messages_in_order)

    @staticmethod
    def test_should_call_attached_callback_function() -> None:
        ...


class TestIrun:
    @staticmethod
    @pytest.mark.parametrize("steps", [-1, 0, 1, 4])
    def test_should_increase_maxsteps_according_to_steps(
        steps: int, dynamics: Dynamics
    ) -> None:
        start_step = dynamics.nsteps
        _ = next(dynamics.irun(steps=steps))
        assert dynamics.max_steps == start_step + steps

    @staticmethod
    def test_should_log_initial_step_when_nsteps_is_zero() -> None:
        ...

    @staticmethod
    def test_should_not_log_initial_step_when_steps_is_nonzero() -> None:
        ...

    @staticmethod
    def test_should_write_trajectory_if_none() -> None:
        ...

    @staticmethod
    def test_should_not_step_if_converged_already() -> None:
        ...

    @staticmethod
    def test_should_return_true_if_converged() -> None:
        ...

    @staticmethod
    def test_should_return_false_if_unconverged(dynamics: Dynamics) -> None:
        steps_unconverged: List[bool] = []
        for converged in dynamics.irun(steps=10):
            steps_unconverged.append(not converged)
        assert all(steps_unconverged)

    @staticmethod
    def test_should_not_step_if_nsteps_not_less_than_maxsteps() -> None:
        ...

    @staticmethod
    @pytest.mark.parametrize("steps", [0, 1, 4])
    def test_should_run_until_step_limit_if_not_converged(
        steps: int, dynamics: Dynamics
    ) -> None:
        start_step = dynamics.nsteps
        for _ in dynamics.irun(steps=steps):
            pass

        assert (dynamics.nsteps - start_step) == steps

    @staticmethod
    def test_should_log_initial_state() -> None:
        ...

    @staticmethod
    def test_should_yield_in_initial_state() -> None:
        ...

    @staticmethod
    @pytest.mark.parametrize("steps,start_step", product([0, 1, 4], [-1, 0, 1]))
    def test_should_increment_nsteps_to_match_total_iterations(
        steps: int, start_step: int, dynamics: Dynamics
    ) -> None:
        steps_match: List[int] = []
        dynamics.nsteps = start_step

        for i, _ in enumerate(dynamics.irun(steps=steps)):
            steps_match.append(i + start_step == dynamics.nsteps)

        assert all(steps_match)


class TestRun:
    @staticmethod
    def test_should_not_run_if_steps_is_zero() -> None:
        ...

    @staticmethod
    def test_should_run_until_step_limit_if_not_converged() -> None:
        ...

    @staticmethod
    def test_should_return_false_if_not_converged() -> None:
        ...

    @staticmethod
    def test_should_return_true_if_not_converged() -> None:
        ...
