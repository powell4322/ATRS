@echo off
setlocal
pushd "%~dp0.." || exit /b 1
set "PYTHON_EXE=.venv\Scripts\python.exe"
set "CONFIG=experiments/ml1m_sasrec.json"

if not exist "%PYTHON_EXE%" (
  echo Missing %PYTHON_EXE%. Create the virtual environment first. 1>&2
  popd
  exit /b 2
)

"%PYTHON_EXE%" -c "import torch; assert torch.cuda.is_available(), 'CUDA is unavailable to PyTorch'; print(torch.__version__, torch.cuda.get_device_name(0))"
if errorlevel 1 goto :failed
"%PYTHON_EXE%" -m atrs.cli preprocess --config "%CONFIG%"
if errorlevel 1 goto :failed
"%PYTHON_EXE%" -m atrs.cli train-teacher --config "%CONFIG%" --defense none --device cuda
if errorlevel 1 goto :failed
"%PYTHON_EXE%" -m atrs.cli train-teacher --config "%CONFIG%" --defense gro --device cuda
if errorlevel 1 goto :failed
"%PYTHON_EXE%" -m atrs.cli train-teacher --config "%CONFIG%" --defense continued-clean --device cuda
if errorlevel 1 goto :failed

for %%D in (none gro continued-clean) do (
  for %%A in (dfme become) do (
    "%PYTHON_EXE%" -m atrs.cli run-attack --config "%CONFIG%" --defense %%D --attack %%A --device cuda
    if errorlevel 1 goto :failed
  )
)

"%PYTHON_EXE%" scripts\export_results.py --config "%CONFIG%"
if errorlevel 1 goto :failed

popd
exit /b 0

:failed
set "STATUS=%ERRORLEVEL%"
echo Experiment matrix stopped with exit code %STATUS%. 1>&2
popd
exit /b %STATUS%
