import pytest
import subprocess
import json

@pytest.mark.environment_test
def test_python_package_import():
    try:
        import CHEM10_Harvard
    except ImportError as e:
        pytest.fail(f"Failed to import CHEM10_Harvard: {e}")
    
    try:
        import numpy
    except ImportError as e:
        pytest.fail(f"Failed to import numpy: {e}")
    
    try:
        subprocess.run(["arduino-cli", "-v"], check=True, text=True, capture_output=True)
    except FileNotFoundError as e:
        pytest.fail(f"arduino-cli not found on PATH: {e}")
    except subprocess.CalledProcessError as e:
        pytest.fail(f"Failed to run arduino-cli.\nexit code: {e.returncode}\nstdout:\n{e.stdout}\nstderr:\n{e.stderr}")

@pytest.mark.environment_test
def test_kernel_has_CHEM10_Harvard():
    # Get a json formatted list of all available kernels
    try:
        res = subprocess.run(["jupyter", "kernelspec", "list", "--json"], check=True, text=True, capture_output=True)
    except FileNotFoundError as e:
        pytest.fail(f"`jupyter` not found on PATH: {e}")
    except subprocess.CalledProcessError as e:
        pytest.fail(f"Failed to list Jupyter kernels.\nexit code: {e.returncode}\nstdout:\n{e.stdout}\nstderr:\n{e.stderr}")

    # Parse the output to get the kernelspecs
    try:
        data = json.loads(res.stdout)
        kernels = data.get("kernelspecs", {})
    except Exception as e:
        pytest.fail(f"Could not parse `jupyter kernelspec list --json` output: {e}\nRaw:\n{res.stdout}")

    if not kernels:
        pytest.fail("No Jupyter kernels found (kernelspecs is empty).")

    # Try each kernel until one can import CHEM10_Harvard (get python executable, then try to import CHEM10_Harvard)
    failures = []
    for name, info in kernels.items():
        spec = info.get("spec") or {}
        argv = spec.get("argv") or []
        if not argv:
            failures.append(f"{name}: missing spec.argv")
            continue

        py_exe = argv[0]  # the python executable the kernel would use
        try:
            imp = subprocess.run([py_exe, "-c", "import CHEM10_Harvard; print(getattr(CHEM10_Harvard, '__file__', '<namespace>'))"], check=True, text=True, capture_output=True,)
            return
        except FileNotFoundError as e:
            failures.append(f"{name}: python exe not found ({py_exe}): {e}")
        except subprocess.CalledProcessError as e:
            failures.append(f"{name}: import failed using {py_exe}\n  exit code: {e.returncode}\n  stdout: {e.stdout.strip()}\n  stderr: {e.stderr.strip()}")
    pytest.fail("No Jupyter kernel found whose Python can import `CHEM10_Harvard`.\n\n" + "\n\n".join(failures))